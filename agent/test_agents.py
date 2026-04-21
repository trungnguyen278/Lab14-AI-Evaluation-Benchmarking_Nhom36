"""Quick test: run one question through V1 and V2, print JSON side-by-side."""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.main_agent import MainAgent


async def main():
    question = "SLA xử lý ticket P1 là bao lâu?"
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])

    print(f"📝 Câu hỏi: {question}\n")

    v1 = MainAgent(version="v1")
    v2 = MainAgent(version="v2")

    print("=" * 60)
    print("🔴 Agent V1 (Base)")
    print("=" * 60)
    r1 = await v1.query(question)
    print(json.dumps(r1, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("🟢 Agent V2 (Optimized)")
    print("=" * 60)
    r2 = await v2.query(question)
    print(json.dumps(r2, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
