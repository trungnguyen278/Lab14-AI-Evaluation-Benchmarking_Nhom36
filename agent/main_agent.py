import asyncio
from typing import Dict

from agent.rag_agent_v1 import RagAgentV1
from agent.rag_agent_v2 import RagAgentV2


class MainAgent:
    """Factory wrapper — switch RAG version via constructor."""

    def __init__(self, version: str = "v1"):
        if version == "v2":
            self._agent = RagAgentV2()
        else:
            self._agent = RagAgentV1()
        self.name = self._agent.name

    async def query(self, question: str) -> Dict:
        return await self._agent.query(question)


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
