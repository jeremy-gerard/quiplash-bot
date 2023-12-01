import os
from time import sleep
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def check_exit_condition():
    if os.path.exists("exit_flag.txt"):
        with open("exit_flag.txt", "r") as file:
            if file.read().strip().lower() == "exit":
                return True
    return False


class QuiplashBot:
    def __init__(self, model="gpt-3.5-turbo"):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.quips = {}
        self.round = 0
        try:
            self.driver = webdriver.Chrome()
            self.driver.get("https://jackbox.tv/")
        except Exception as e:
            print(f"An error occurred: {e}")

    def join_game(self, roomcode, username):
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, "roomcode"))
        )
        self.driver.find_element(By.ID, "roomcode").send_keys(roomcode)
        self.driver.find_element(By.ID, "username").send_keys(username)
        sleep(1)
        self.driver.find_element(By.ID, "button-join").click()

    def _check_state(self):
        if "pt-page-off" not in self.driver.find_element(
            By.ID, "state-answer-question"
        ).get_attribute("class"):
            return "answer-question"

        if "pt-page-off" not in self.driver.find_element(
            By.ID, "state-vote"
        ).get_attribute("class"):
            return "vote"

        if "pt-page-off" not in self.driver.find_element(
            By.ID, "state-lobby"
        ).get_attribute("class"):
            return "lobby"

        if "pt-page-off" not in self.driver.find_element(
            By.ID, "state-logo"
        ).get_attribute("class"):
            return "logo"

        if "pt-page-off" not in self.driver.find_element(
            By.ID, "state-round"
        ).get_attribute("class"):
            return "round"

        if "pt-page-off" not in self.driver.find_element(
            By.ID, "state-done-answering"
        ).get_attribute("class"):
            return "done-answering"

        return "error"

    def play(self):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "state-lobby"))
        )
        state = "start"
        while True:
            if state != self._check_state():
                print(f"state: {state}")

                if any([state == "lobby", state == "logo", state == "done"]):
                    pass

                if state == "round":
                    self.round += 1
                    print(f"\nStarting Round {self.round}\n")
                    if self.round == 3:
                        self._answer_last_lash()
                    else:
                        self._answer_question()

                if state == "done-answering" or state == "vote":
                    if self.round == 3:
                        self._vote_last_lash()
                    else:
                        self._vote()

                sleep(1)
                state = self._check_state()

            if check_exit_condition():
                print("Exit condition met. Stopping the bot.")
                break

    def _answer_question(self):
        WebDriverWait(self.driver, 60).until(
            EC.visibility_of_element_located((By.ID, "state-answer-question"))
        )
        print("answering questions...")
        while self._check_state() == "answer-question":
            question = self.driver.find_element(By.ID, "question-text").text
            if question not in self.quips.keys():
                quip = self._get_quip(question)
                WebDriverWait(self.driver, 20).until(
                    EC.visibility_of_element_located((By.ID, "quiplash-answer-input"))
                )
                self.driver.find_element(By.ID, "quiplash-answer-input").send_keys(quip)
                self.driver.find_element(By.ID, "quiplash-submit-answer").click()
                self.quips[question] = quip
            else:
                sleep(1)

    def _get_quip(self, question):
        prompt = f"""
        We're playing the game Quiplash.  I'll give you a prompt below, \\
        and you have to give me a funny answer in 20 characters or fewer. \n\n
        {question}
        """
        return (
            self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
            )
            .choices[0]
            .message.content.replace('"', "")
            .strip()
        )

    def _vote(self):
        questions = []
        while self._check_state() in ["logo", "vote"]:
            question = (
                self.driver.find_element(By.ID, "state-vote")
                .find_element(By.ID, "question-text")
                .text
            )
            if question not in questions and len(question) > 0:
                questions.append(question)
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, 'button[data-vote="left"]')
                        )
                    )
                    response_1 = self.driver.find_element(
                        By.CSS_SELECTOR, 'button[data-vote="left"]'
                    ).text
                    response_2 = self.driver.find_element(
                        By.CSS_SELECTOR, 'button[data-vote="right"]'
                    ).text

                    vote = self._get_vote(question, response_1, response_2)
                    print(f"vote: {vote}")
                    if vote.__contains__("1"):
                        self.driver.find_element(
                            By.CSS_SELECTOR, 'button[data-vote="left"]'
                        ).click()
                    elif vote.__contains__("2"):
                        self.driver.find_element(
                            By.CSS_SELECTOR, 'button[data-vote="right"]'
                        ).click()
                    else:
                        print(f"Malformed vote response: {vote}")
                    break
                except Exception:
                    continue

    def _get_vote(self, question, response_1, response_2):
        prompt = f"""
        We’re playing the game Quiplash.  I’ll provide you with a \\
        prompt and then 2 responses from other players.  Select which \\
        one you think is funnier by responding with the number only. \\
        If you don't know, just respond randomly with 1 or 2. \n\n
        {question}
        1: {response_1}
        2: {response_2}
        """
        print(prompt)
        return (
            self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
            )
            .choices[0]
            .message.content.replace('"', "")
            .strip()
        )

    def _answer_last_lash(self):
        try:
            question_text = (
                self.driver.find_element(By.ID, "question-text-alt").text
                + " "
                + self.driver.find_element(By.ID, "question-text").text
            )
            answer = self._get_quip(question_text)
            print(answer)
            self.driver.find_element(By.ID, "quiplash-answer-input").send_keys(answer)
            self.driver.find_element(By.ID, "quiplash-submit-answer").click()
        except Exception as e:
            print(e)

    def _vote_last_lash(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'button[data-vote="1"]')
                )
            )
            question = self.driver.find_element(By.ID, "question-text").text
            responses = []
            for i in range(1, 8):
                try:
                    responses.append(
                        self.driver.find_element(
                            By.CSS_SELECTOR, f'button[data-vote="{i}"]'
                        ).text
                    )
                except Exception:
                    continue
            vote = self._get_vote_last_lash(question, responses)
            for i in range(1, 8):
                if vote.__contains__(str(i)):
                    self.driver.find_element(
                        By.CSS_SELECTOR, f'button[data-vote="{i}"]'
                    ).click()
                    break
        except Exception as e:
            print(e)

    def _get_vote_last_lash(self, question, responses):
        prompt = f"""
        We’re playing the game Quiplash.  I’ll provide you with a prompt \\
        and then {len(responses)} responses from other players. Select \\
        which one you think is funniest by responding with the number only.\n
        Prompt: "{question}"\n
        """
        for response in responses:
            prompt += f"{responses.index(response)+1}: {response}\n"
        print(prompt)
        return (
            self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
            )
            .choices[0]
            .message.content.replace('"', "")
            .strip()
        )
