from __future__ import annotations

import copy
import logging
from operator import itemgetter
from typing import Any, Dict, List, Optional, Tuple, Union

from lm_eval.models.openai_completions import LocalCompletionsAPI

logger = logging.getLogger(__name__)


class LlamaCppCompletionsAPI(LocalCompletionsAPI):
    """Drop-in replacement for LocalCompletionsAPI that evaluates against a
    locally loaded GGUF via llama_cpp instead of an HTTP llama-server.

    llama-server's OpenAI endpoint only returns logprobs for *generated*
    tokens (``logprobs.content``), which breaks lm_eval's loglikelihood
    tasks.  llama_cpp with ``logits_all=True`` + ``echo=True`` returns the
    legacy ``token_logprobs``/``top_logprobs`` per *prompt* token, which is
    exactly the format lm_eval's ``parse_logprobs`` expects.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 2048,
        n_gpu_layers: int = 99,
        seed: int = 1234,
        tokenizer=None,
        **kwargs,
    ):
        super().__init__(
            tokenizer=tokenizer,
            tokenizer_backend="huggingface",
            tokenized_requests=True,
            seed=seed,
            **kwargs,
        )
        self.model_path = model_path
        self._n_ctx = int(n_ctx)
        self._n_gpu_layers = int(n_gpu_layers)
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            if not self.model_path:
                raise ValueError("model_path is required for LlamaCppCompletionsAPI")
            from llama_cpp import Llama

            logger.info("loading GGUF for evaluation: %s", self.model_path)
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self._n_ctx,
                n_gpu_layers=self._n_gpu_layers,
                verbose=False,
                seed=self._seed,
                logits_all=True,
            )
            logger.info("GGUF loaded for evaluation")
        return self._llm

    def model_call(
        self,
        messages: Union[List[List[int]], List[str], List[Any]],
        *,
        generate: bool = True,
        gen_kwargs: Optional[Dict] = None,
        **kwargs,
    ) -> Optional[dict]:
        gen_kwargs = copy.deepcopy(gen_kwargs)
        payload = self._create_payload(
            self.create_message(messages),
            generate=generate,
            gen_kwargs=gen_kwargs,
            seed=self._seed,
            eos=self.eos_string,
            **kwargs,
        )
        prompt = payload.pop("prompt")
        payload.pop("model", None)
        try:
            llm = self._get_llm()
            if isinstance(prompt, list) and prompt and isinstance(prompt[0], list):
                if len(prompt) == 1:
                    prompt = prompt[0]
                else:
                    return [self._call(llm, p, generate, payload) for p in prompt]
            return self._call(llm, prompt, generate, payload)
        except Exception as e:  # surface as retryable failure like HTTP errors
            logger.warning("llama_cpp request failed: %s", e)
            raise e

    def _call(self, llm, prompt, generate, payload) -> dict:
        # llama_cpp's echo path does `prompt + text_str`, so it requires a
        # string prompt (a token list breaks it). Decode the HF token ids back
        # to text; the round-trip is lossless for the shared Qwen vocab.
        if isinstance(prompt, list) and not generate:
            prompt = self.tokenizer.decode(prompt, skip_special_tokens=False)
        return llm.create_completion(prompt=prompt, **payload)

    @staticmethod
    def parse_logprobs(
        outputs: Union[Dict, List[Dict]],
        tokens: List[List[int]] = None,
        ctxlens: List[int] = None,
        **kwargs,
    ) -> List[Tuple[float, bool]]:
        """Parse logprobs from llama_cpp echo output.

        llama_cpp may or may not append a generated token after the echoed
        prompt, so we slice the continuation region by the token length of the
        request rather than relying on a trailing generated token.
        """
        res = []
        if not isinstance(outputs, list):
            outputs = [outputs]
        for out in outputs:
            for i, choice in enumerate(
                sorted(out["choices"], key=itemgetter("index"))
            ):
                ctxlen = ctxlens[i]
                assert ctxlen > 0, "Context length must be greater than 0"
                lps = choice["logprobs"]["token_logprobs"]
                tops = choice["logprobs"]["top_logprobs"]
                # Continuation covers [ctxlen, len(prompt tokens)); a trailing
                # generated token (if present) is excluded automatically.
                cont_len = len(tokens[i]) - ctxlen if tokens is not None else 1
                continuation_lps = lps[ctxlen : ctxlen + cont_len]
                continuation_tops = tops[ctxlen : ctxlen + cont_len]
                logprobs = sum(continuation_lps)
                is_greedy = True
                for tok, top in zip(continuation_lps, continuation_tops):
                    if tok != max(top.values()):
                        is_greedy = False
                        break
                res.append((logprobs, is_greedy))
        return res
