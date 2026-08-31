# agent/run.py
import os
from dotenv import load_dotenv

from agent import agent_executor

load_dotenv()

def cli():
    print("CLI-агент. Введите 'exit' для выхода.")
    while True:
        user_input = input("\nВы: ")
        if user_input.lower() == "exit":
            print("До свидания!")
            break
        try:
            result = agent_executor.invoke({"input": user_input})
            output = result.get("output", str(result))
            print("Агент:", output)
        except Exception as e:
            print("Ошибка:", e)

if __name__ == "__main__":
    cli()