from __future__ import annotations

from typing import Any, Iterator, Type

_STUB_OUT = "任务已完成：通过 MCP 调用 submit_artifact 成功提交，review 通过，approve_pr 后 squash merge 合并。节点状态已变为 done。"


class _StubResponse:
    def __init__(self, content: str) -> None:
        self.content = content

    def __str__(self) -> str:
        return self.content


class _StubAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.type = "ai"
        try:
            from langchain_core.messages import AIMessage

            self.__class__ = type(
                "StubAIMsg", (AIMessage,), {}
            )
        except Exception:
            pass


class _StubRunnable:
    def __init__(self, llm_mock: "LLMMock") -> None:
        self._llm = llm_mock

    def invoke(self, *args: Any, **kwargs: Any) -> _StubResponse:
        return self._llm.invoke(*args, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> _StubResponse:
        return self.invoke(*args, **kwargs)

    def __or__(self, other: Any) -> "_StubRunnable":
        return self

    def __ror__(self, other: Any) -> "_StubRunnable":
        return self

    def pipe(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return self

    def with_config(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return self

    def with_retry(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return self

    def with_fallbacks(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return self

    def assign(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return self

    def pick(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return self

    def stream(self, *args: Any, **kwargs: Any) -> Iterator[_StubResponse]:
        yield self.invoke(*args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> _StubResponse:
        return self.invoke(*args, **kwargs)

    def batch(self, inputs: list, **kwargs: Any) -> list:
        return [self.invoke(x, **kwargs) for x in inputs]

    def getName(self) -> str:
        return "StubRunnable"

    @property
    def InputType(self) -> Any:
        return Any

    @property
    def OutputType(self) -> Any:
        return str


class LLMMock:
    _llm_type = "mock_llm"
    lc_serializable = False
    lc_secrets: dict = {}
    lc_attributes: dict = {}

    def __init__(self, stub_output: str | None = None) -> None:
        self._stub = stub_output or _STUB_OUT
        self.call_count = 0
        self.last_prompt: Any = None
        self.last_bind_kwargs: dict[str, Any] = {}

    @property
    def _identifying_params(self) -> dict:
        return {"model": "mock-stub-model", "class": "LLMMock"}

    def invoke(self, prompt: Any, **kwargs: Any) -> _StubResponse:
        self.call_count += 1
        self.last_prompt = prompt
        return _StubResponse(self._stub)

    def _generate(self, prompts: list, **kwargs: Any):
        self.call_count += 1
        self.last_prompt = prompts

        class _StubGenResult:
            def __init__(self, text: str) -> None:
                self.generations = [[type("G", (), {"text": text, "message": _StubAIMessage(text)})()]]
                self.llm_output = {"token_usage": {"total_tokens": 1}}

        return _StubGenResult(self._stub)

    def generate(self, prompts: list, **kwargs: Any):
        return self._generate(prompts, **kwargs)

    def agenerate(self, prompts: list, **kwargs: Any):
        return self._generate(prompts, **kwargs)

    def predict(self, *args: Any, **kwargs: Any) -> str:
        self.call_count += 1
        return self._stub

    def predict_messages(self, messages: list, **kwargs: Any) -> _StubAIMessage:
        self.call_count += 1
        self.last_prompt = messages
        return _StubAIMessage(self._stub)

    def __call__(self, *args: Any, **kwargs: Any) -> _StubResponse:
        return self.invoke(*args, **kwargs)

    def bind(self, **kwargs: Any) -> "_StubRunnable":
        bound = LLMMock(self._stub)
        bound.last_bind_kwargs = dict(kwargs)
        bound.call_count = self.call_count
        return _StubRunnable(bound)

    def with_retry(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return _StubRunnable(self)

    def with_config(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return _StubRunnable(self)

    def with_fallbacks(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return _StubRunnable(self)

    def pipe(self, *args: Any, **kwargs: Any) -> "_StubRunnable":
        return _StubRunnable(self)

    def __or__(self, other: Any) -> "_StubRunnable":
        return _StubRunnable(self)

    def __ror__(self, other: Any) -> "_StubRunnable":
        return _StubRunnable(self)

    def stream(self, input: Any, **kwargs: Any) -> Iterator[_StubResponse]:
        yield self.invoke(input, **kwargs)

    def astream(self, input: Any, **kwargs: Any) -> Any:
        import asyncio

        async def _gen():
            yield self.invoke(input, **kwargs)

        return _gen()

    async def ainvoke(self, input: Any, **kwargs: Any) -> _StubResponse:
        return self.invoke(input, **kwargs)

    @property
    def completions(self) -> "LLMMock":
        return self

    @property
    def chat(self) -> "LLMMock":
        return self

    def get_token_ids(self, text: str) -> list[int]:
        return list(range(min(len(text), 10)))

    def get_num_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def get_num_tokens_from_messages(self, messages: list) -> int:
        return 10
