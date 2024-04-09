import os
import openai
from typing_extensions import override
from openai import AssistantEventHandler
import time

os.environ["OPENAI_API_KEY"] = "채웡"
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
#######################################################################################


class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\n서강gpt > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)


def query(assistant_id, user, thread_id, question):
    with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            instructions=question,
            event_handler=EventHandler(),
    ) as stream:
        stream.until_done()


def loop(a_id, t_id):
    while True:
        print("당신>", end="")
        query(a_id, 0, t_id, input())
        print("\n")


def main():
    assistant_id = "asst_iU8eJSpSVD9xQ3GoH9a46SsB"
    thread_id = "thread_B0heHPmZQ4N1SxzgGF692HKx"
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    os.system("cls")
    for i, message in enumerate(reversed(messages.data), start=1):
        print("서강gpt>" if message.role == "assistant" else "당신>", end="")
        for content in message.content:
            print(content.text.value+"\n")
    loop(assistant_id, thread_id)


main()
