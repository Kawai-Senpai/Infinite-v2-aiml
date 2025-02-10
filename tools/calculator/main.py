from .core import calculate

#? Required ------------------------------------------------------------------
_info = "This allows you to perform mathematic calculations."
_author = "Ranit"
_group = "InfiniteRegen"
_type = "official" #available types are: official, thirdparty

def _execute(agent, message, history):
    """Main function to execute the web search tool"""
    return calculate(message)