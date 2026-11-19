# Run with calibre-debug -e: adds 70 dummy books to a throwaway dev library (for scrolling tests).
import sys

from calibre.ebooks.covers import generate_cover
from calibre.ebooks.metadata.book.base import Metadata
from calibre.library import db

d = db(sys.argv[-1]).new_api
for i in range(70):
    mi = Metadata(f'Sample Volume {i + 1}', [f'Author {i % 9 + 1}'])
    mi.tags = ['Samples']
    bid = d.create_book_entry(mi)
    d.set_cover({bid: generate_cover(mi)})
print('books', len(d.all_book_ids()))
