from __future__ import annotations

import asyncio
from .state import GraphState
from .graph import build_app
import uuid


async def main(query: str):
    app = build_app()
    state = GraphState(query=query)
    thread_id = state.thread_id or f"th_{uuid.uuid4().hex[:8]}"
    state.thread_id = thread_id
    config = {"configurable": {"thread_id": thread_id}}
    result = await app.ainvoke(state, config)
    return result


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "latest ai news"
    out = asyncio.run(main(q))
    print('\n\nout is the graph state:\n', out.keys(),'\n\n')
    print(out['final_text'])



