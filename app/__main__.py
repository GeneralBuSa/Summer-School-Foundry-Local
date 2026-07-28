"""`python -m app ingest` ve `python -m app chat` komutlarının giriş noktası."""

from __future__ import annotations

import argparse
import sys

from app.chat import answer_question, print_answer
from app.config import DATABASE_PATH
from app.foundry import FoundryRuntime, FoundryRuntimeError
from app.ingest import run_ingest
from app.repository import RepositoryError, SQLiteRepository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline SQLite + Foundry Local RAG asistanı")
    parser.add_argument("command", choices=("ingest", "chat", "ui", "watch", "eval"), help="Çalıştırılacak işlem")
    parser.add_argument("--force-reindex", action="store_true", help="Embedding modeli değişmiş olsa bile tüm belgeleri yeniden indeksle")
    return parser


def _chat_loop(repository: SQLiteRepository, runtime: FoundryRuntime) -> None:
    print('Soru sorun. Çıkmak için "quit" veya "exit" yazın.')
    history: list[dict[str, str]] = []
    while True:
        try:
            question = input("\nSoru: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGüvenli şekilde çıkılıyor.")
            return
        if question.lower() in {"quit", "exit"}:
            return
        if not question:
            print("Lütfen boş olmayan bir soru yazın.")
            continue
        answer = answer_question(question, repository, runtime, chat_history=history)
        print_answer(answer)
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer.text}])


def main() -> int:
    args = _parser().parse_args()
    if args.command == "ui":
        import subprocess
        import sys
        print("Streamlit Web Arayüzü başlatılıyor...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/ui.py"])
        return 0

    if args.command == "watch":
        from app.watcher import watch_forever
        watch_forever(SQLiteRepository(DATABASE_PATH))
        return 0

    if args.command == "eval":
        from tests.eval_retrieval import run_eval
        return run_eval()

    repository = SQLiteRepository(DATABASE_PATH)
    try:
        with FoundryRuntime() as runtime:
            if args.command == "ingest":
                summary = run_ingest(repository, runtime, force_reindex=args.force_reindex)
                print(
                    f"İndeksleme tamamlandı: {summary.indexed_documents} belge, "
                    f"{summary.chunk_count} parça eklendi; {summary.skipped_documents} belge atlandı."
                )
            else:
                _chat_loop(repository, runtime)
    except (FoundryRuntimeError, RepositoryError, ValueError, RuntimeError) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
