from utils.DataBaseBuilder.parsers.aldi_parser import AldiParser
from utils.DataBaseBuilder.parsers.other_parser import OtherParser
from utils.DataBaseBuilder.parsers.publix_parser import PublixParser
from utils.DataBaseBuilder.parsers.trader_joes_parser import TraderJoesParser


PARSERS = {
    "1": PublixParser,
    "2": TraderJoesParser,
    "3": AldiParser,
    "4": OtherParser,
}


def build_parser(option: str):
    parser_class = PARSERS.get(option)

    if parser_class is None:
        return None

    return parser_class()
