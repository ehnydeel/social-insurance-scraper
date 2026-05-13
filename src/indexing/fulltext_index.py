from whoosh.index import create_in
from whoosh.fields import *

schema = Schema(
    title=TEXT(stored=True),
    content=TEXT(stored=True),
    path=ID(stored=True)
)