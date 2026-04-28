import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search import answer_question


def main() -> None:
    print("Sistema de perguntas sobre PDF. Digite 'exit' ou 'quit' para sair.\n")
    while True:
        try:
            pergunta = input("PERGUNTA: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando. Até logo!")
            break

        if pergunta.lower() in ("exit", "quit"):
            print("Encerrando. Até logo!")
            break

        if not pergunta:
            continue

        resposta = answer_question(pergunta)
        print(f"RESPOSTA: {resposta}\n")


if __name__ == "__main__":
    main()
