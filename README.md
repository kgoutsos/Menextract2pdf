# Menextract2pdf
**Extract Mendeley annotations to PDF Files**

Menextract2pdf extracts highlights and notes from the Mendeley database and adds them directly to corresponding PDF files, which can then be read by most PDF readers.

## Why?

PDF highlights and notes in Mendeley are stored in the Mendeley database and cannot be read by other programs. While it is possible to export the annotations through Mendeley, the results are questionable and often look bad. Menextract2pdf provides a bulk export functionality.

## Dependencies

The latest version of Menextract2pdf requires Python3. See [requirements.txt](requirements.txt) for the required packages.

It further incorporates pdfannotation.py from the [PRSAnnots](https://github.com/rschroll/prsannots) project, with small adjustments.

## Usage

```python
python menextract2pdf.py mendeley.sqlite /destination_directory/
```
where mendeley.sqlite is the mendeley database and /Destination/Dir/ is the directory where to store the annotated PDF files. By default menextract2pdf will not overwrite existing PDF files in the destination directory. To allow overwriting use the ```--overwrite``` flag.

The code is tested on Linux, but should run on Windows or Mac as well.

## Known issues

- "zlib error, skipping file": This is due to "corrupted" PDF files. A workaround would be to use ghostscript to repair the file and try again: ```gs -o repaired.pdf -dQUIET -sDEVICE=pdfwrite damaged.pdf```

- "Empty URL found for document": Usually means that the specified document has not been downloaded to your local machine. Open the document in Mendeley to force the download and try again.

## Versions

* 0.1 first release

## Licence

The script is distributed under the GPLv3. The pdfannotations.py file is LGPLv3.

## Related projects

* [Mendeley2Zotero](https://github.com/flinz/mendeley2zotero)
* [Adios_Mendeley](https://github.com/rdiaz02/Adios_Mendeley)
