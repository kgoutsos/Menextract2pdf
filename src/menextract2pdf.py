# Copyright 2016 Jochen Schroeder
#
# This file is distributed under the terms of the
# GPLv3 licence. See the COPYING file for details

import sqlite3
from urllib.parse import unquote, urlparse
import os
import pdfannotation
import PyPDF2
import warnings
from dateutil import parser as dtparser
import sys
import zlib

global OVERWRITE_PDFS
OVERWRITE_PDFS = False

def convert2datetime(s):
    return dtparser.parse(s)

def converturl2abspath(url):
    """Convert a url string to an absolute path"""
    return os.path.abspath(unquote(urlparse(url).path))

def get_document_title_from_db(db, file_hash):
    query = "SELECT Documents.title from Documents where Documents.id in (SELECT DocumentFiles.documentId from DocumentFiles where DocumentFiles.hash == ?)"
    results = db.execute(query, (file_hash,)).fetchall()
    return results[0][0] if len(results) == 1 else None

def get_highlights_from_db(db, results={}):
    """Extract the locations of highlights from the Mendeley database
    and put results into dictionary.

    Parameters
    ==========
    db :    sqlite3.connection
        Mendeley sqlite database
    results : dict, optional
        Dictionary to hold the results. Default is an empty dictionary.

    Returns
    =======
    results : dict
        dictionary containing the query results
    """
    query = """SELECT Files.localUrl, FileHighlightRects.page,
                            FileHighlightRects.x1, FileHighlightRects.y1,
                            FileHighlightRects.x2, FileHighlightRects.y2,
                            FileHighlights.createdTime, FileHighlights.color,
                            Files.hash
                    FROM Files
                    LEFT JOIN FileHighlights
                        ON FileHighlights.fileHash=Files.hash
                    LEFT JOIN FileHighlightRects
                        ON FileHighlightRects.highlightId=FileHighlights.id
                    WHERE (FileHighlightRects.page IS NOT NULL)"""
    ret = db.execute(query)
    for r in ret:
        if r[0] != "":
            pth = converturl2abspath(r[0])
        else:
            pth = get_document_title_from_db(db, r[8])
            results[pth] = None
            continue
        pg = r[1]
        bbox = [[r[2], r[3], r[4], r[5]]]
        cdate = convert2datetime(r[6])
        color = r[7]
        hlight = {"rect": bbox, "cdate": cdate, "color": color}
        if pth in results:
            if pg in results[pth]:
                if 'highlights' in results[pth][pg]:
                    results[pth][pg]['highlights'].append(hlight)
                else:
                    results[pth][pg]['highlights'] = [hlight]
            else:
                results[pth][pg] = {'highlights': [hlight]}
        else:
            results[pth] = {pg: {'highlights':[hlight]}}
    return results

def get_notes_from_db(db, results={}):
    """Extract notes from the Mendeley database
    and put results into dictionary.

    Parameters
    ==========
    db :    sqlite3.connection
        Mendeley sqlite database
    results : dict, optional
        Dictionary to hold the results. Default is an empty dictionary.

    Returns
    =======
    results : dict
        dictionary containing the query results
    """
    query = """SELECT Files.localUrl, FileNotes.page,
                            FileNotes.x, FileNotes.y,
                            FileNotes.author, FileNotes.note,
                            FileNotes.modifiedTime, FileNotes.color,
                            Files.hash
                    FROM Files
                    LEFT JOIN FileNotes
                        ON FileNotes.fileHash=Files.hash
                    WHERE FileNotes.page IS NOT NULL"""
    ret = db.execute(query)
    for r in ret:
        if r[0] != "":
            pth = converturl2abspath(r[0])
        else:
            pth = get_document_title_from_db(db, r[8])
            results[pth] = None
            continue
        pg = r[1]
        bbox = [r[2], r[3], r[2]+30, r[3]+30] # needs a rectangle however size does not matter
        author = r[4]
        txt = r[5]
        cdate = convert2datetime(r[6])
        color = r[7]
        note = {"rect": bbox, "author": author, "content": txt, "cdate":cdate, "color": color}
        if pth in results:
            if pg in results[pth]:
                if 'notes' in results[pth][pg]:
                    results[pth][pg]['notes'].append(note)
                else:
                    results[pth][pg]['notes'] = [note]
            else:
                results[pth][pg] = {'notes': [note]}
        else:
            results[pth] = {pg: {'notes':[note]}}
    return results

def add_annotation2pdf(inpdf, outpdf, annotations):
    for pg in range(1, inpdf.getNumPages()+1):
        inpg = inpdf.getPage(pg-1)
        if pg in annotations.keys():
            if 'highlights' in annotations[pg]:
                for hn in annotations[pg]['highlights']:
                    if hn['color'] is not None:
                        annot = pdfannotation.highlight_annotation(hn["rect"], cdate=hn["cdate"], color=hn["color"])
                    else:
                        annot = pdfannotation.highlight_annotation(hn["rect"], cdate=hn["cdate"])
                    pdfannotation.add_annotation(outpdf, inpg, annot)
            if 'notes' in annotations[pg]:
                for nt in annotations[pg]['notes']:
                    if nt['color'] is not None:
                        note = pdfannotation.text_annotation(nt["rect"], contents=nt["content"], author=nt["author"],
                                                             color=nt["color"], cdate=nt["cdate"])
                    else:
                        note = pdfannotation.text_annotation(nt["rect"], contents=nt["content"], author=nt["author"],
                                                             cdate=nt["cdate"])
                    pdfannotation.add_annotation(outpdf, inpg, note)
        outpdf.addPage(inpg)
    return outpdf

def processpdf(fn, fn_out, annotations):
    try:
        inpdf = PyPDF2.PdfFileReader(open(fn, 'rb'), strict=False)
        if inpdf.isEncrypted:
            # PyPDF2 seems to think some files are encrypted even
            # if they are not. We just ignore the encryption.
            # This seems to work for the one file where I saw this issue
            inpdf._override_encryption = True
            inpdf._flatten()
    except IOError:
        sys.stderr.write(f"Could not find pdffile {fn}\n.")
        return
    outpdf = PyPDF2.PdfFileWriter()
    outpdf = add_annotation2pdf(inpdf, outpdf, annotations)
    if os.path.isfile(fn_out):
        if not OVERWRITE_PDFS:
            print(f"{fn_out} exists skipping.")
            return
        else:
            print(f"overwriting {fn_out}")
    else:
        print(f"writing pdf to {fn_out}")
    outpdf.write(open(fn_out, "wb"))

def mendeley2pdf(fn_db, dir_pdf):
    if not os.path.isfile(fn_db):
        sys.stderr.write(f"Database file not found: {fn_db}.\n")
        return

    db = sqlite3.connect(fn_db)
    highlights = get_highlights_from_db(db)
    annotations_all = get_notes_from_db(db, highlights)
    for fn, annons in annotations_all.items():
        if annons is None:
            sys.stderr.write(f"Empty URL found for document \"{fn}\".\n")
            continue
        try:
            processpdf(fn, os.path.join(dir_pdf, os.path.basename(fn)), annons)
        except zlib.error:
            sys.stderr.write(f"zlib error, skipping file: {fn}.\n")
        except PyPDF2.utils.PdfStreamError:
            sys.stderr.write(f"I appear to have run out of things to join together on {fn}.\n")
        except PyPDF2.utils.PdfReadError:
            sys.stderr.write(f"I appear to have run out of things to read on {fn}.\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("mendeleydb", help="The mendeley sqlite database file",
                        type=str)
    parser.add_argument("dest", help="""The destination directory where to
                        save the annotated pdfs""", type=str)
    parser.add_argument("-w", "--overwrite", help="""Overwrite any PDF files in
                        the destination directory""", action="store_true")
    args = parser.parse_args()
    fn = os.path.abspath(args.mendeleydb)
    dir_pdf = os.path.abspath(args.dest)
    if args.overwrite:
        OVERWRITE_PDFS = True
    mendeley2pdf(fn, dir_pdf)
