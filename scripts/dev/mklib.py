# Run with calibre-debug -e: builds a throwaway dev library (never the real one).
import sys

from calibre.ebooks.covers import generate_cover
from calibre.ebooks.metadata.book.base import Metadata
from calibre.library import db

BOOKS = '''Pride and Prejudice|Jane Austen||Classics,Romance|4
Emma|Jane Austen||Classics|3
Moby-Dick|Herman Melville||Classics,Adventure|5
The Time Machine|H. G. Wells|Wells Collection|Science Fiction|4
The War of the Worlds|H. G. Wells|Wells Collection|Science Fiction|3
Frankenstein|Mary Shelley||Horror,Classics|5
Dracula|Bram Stoker||Horror|4
The Adventures of Sherlock Holmes|Arthur Conan Doyle|Sherlock Holmes|Mystery|5
The Hound of the Baskervilles|Arthur Conan Doyle|Sherlock Holmes|Mystery|4
Middlemarch|George Eliot||Classics|2
Walden|Henry David Thoreau||Nonfiction|3
Meditations|Marcus Aurelius||Philosophy,Nonfiction|5'''

d = db(sys.argv[-1]).new_api
for i, line in enumerate(BOOKS.splitlines()):
    t, a, s, tags, r = line.split('|')
    mi = Metadata(t, [a])
    if s:
        mi.series, mi.series_index = s, i % 3 + 1
    mi.tags = tags.split(',')
    mi.rating = int(r) * 2
    mi.publisher = 'Public Domain Press'
    mi.comments = f'<p>{t} by {a}. A placeholder description for the theme screenshots.</p>'
    bid = d.create_book_entry(mi)
    d.set_cover({bid: generate_cover(mi)})
print('books', len(d.all_book_ids()))
