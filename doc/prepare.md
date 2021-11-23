# Preparing the data files

The first time the program is run, the MMP eASLRB PDF must be analyzed (to extract some key data), and prepared. The webapp will do this for you automatically, but since there are different versions of the eASLRB (and everyone gets a different file anyway, because of the watermarks), it's possible that the automatic process might fail.

In this case, you can try to prepare the data files manually, which gives you a chance to fix any problems.

The steps below assume that you've created a directory `/tmp/prepared/` to store the prepared files, and `$EASLRB` refers to your copy of the MMP eASLRB PDF file.

*NOTE: If you are running the program using Docker, you will need to perform these steps inside the container.*

### Extract from the eASLRB PDF

The first step is to extract the information we need from the eASLRB PDF.
```
    asl_rulebook2/extract/all.py $EASLRB \
        --format json \
        --save-index /tmp/prepared/ASL\ Rulebook.index \
        --save-targets /tmp/prepared/ASL\ Rulebook.targets \
        --save-chapters /tmp/prepared/ASL\ Rulebook.chapters \
        --save-footnotes /tmp/prepared/ASL\ Rulebook.footnotes \
        --save-vo-notes /tmp/prepared/ASL\ Rulebook.vo-notes \
        --progress
```
This extracts the information we need, and saves it in the 5 data files.

### Prepare the PDF

Next, we need to prepare the eASLRB PDF, namely create bookmarks for each rule, so that the webapp can jump directly to each one:
```
    asl_rulebook2/bin/prepare_pdf.py \
        $EASLRB \
        --targets /tmp/prepared/ASL\ Rulebook.targets \
        --vo-notes /tmp/prepared/ASL\ Rulebook.vo-notes \
        --yoffset 5 \
        --output /tmp/prepared.pdf \
        --compression ebook \
        --progress
```
We also take the opportunity to compress the PDF.

### Fixup the PDF

Finally, we need to fixup some issues in the PDF:
```
    asl_rulebook2/bin/fixup_mmp_pdf.py \
        /tmp/prepared.pdf \
        --rotate \
        --optimize-web \
        --output /tmp/prepared/ASL\ Rulebook.pdf \
        --progress
```
This rotates any landscape pages, so that the browser shows pages at the correct width (without a horizontal scrollbar), and optimizes the PDF for use in a browser.

### Using the prepared files

You should now have 6 files (the 5 extracted data files, plus the fixed-up PDF), which can be passed in to the program e.g.
```
    ./run-container.sh \
        --data /tmp/prepared/
```
