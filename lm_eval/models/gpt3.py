import os
import transformers
from lm_eval.base import LM
from lm_eval import utils
from tqdm import tqdm


def get_result(response, ctxlen):
    is_greedy = True
    logprobs = response["logprobs"]["token_logprobs"]
    continuation_logprobs = sum(logprobs[ctxlen:])

    for i in range(ctxlen, len(response["logprobs"]["tokens"])):
        token = response["logprobs"]["tokens"][i]
        top_tokens = response["logprobs"]["top_logprobs"][i]
        top_token = max(top_tokens.keys(), key=lambda x: top_tokens[x])
        if top_token != token:
            is_greedy = False
            break
    
    return continuation_logprobs, is_greedy


class GPT3LM(LM):

    MAX_LENGTH = 2048
    REQ_CHUNK_SIZE = 64

    def __init__(self, engine, truncate=False):
        """

        :param engine: str
            OpenAI API engine (e.g. davinci)
        :param truncate: bool
            Truncate input if too long (if False and input is too long, throw error)
        """
        import openai
        self.engine = engine
        self.tokenizer = transformers.GPT2TokenizerFast.from_pretrained('gpt2')
        self.truncate = truncate

        # Read from environment variable OPENAI_API_SECRET_KEY
        openai.api_key = os.environ["OPENAI_API_SECRET_KEY"]

    @classmethod
    def create_from_arg_string(cls, arg_string):
        args = utils.simple_parse_args_string(arg_string)
        return cls(engine=args.get("engine", "davinci"))

    def loglikelihood(self, requests):
        import openai
        res = []

        for chunk in tqdm(utils.chunks(requests, self.REQ_CHUNK_SIZE)):
            inps = []
            ctxlens = []
            for context, continuation in chunk:
                print(context)
                context_enc = self.tokenizer.encode(context)
                continuation_enc = self.tokenizer.encode(continuation)
                inp = (context_enc + continuation_enc)[-self.MAX_LENGTH:]
                ctxlen = len(context_enc) - max(0, len(context_enc) + len(continuation_enc) - self.MAX_LENGTH)

                inps.append(inp)
                ctxlens.append(ctxlen)

            response = openai.Completion.create(
                engine=self.engine,
                prompt=inps,
                echo=True,
                max_tokens=0, temperature=0.,
                logprobs=10,
            )

            for resp, ctxlen in zip(response.choices, ctxlens):
                res.append(get_result(resp, ctxlen))
            
        return res

    def greedy_until(self, requests):
        # TODO: implement
        pass