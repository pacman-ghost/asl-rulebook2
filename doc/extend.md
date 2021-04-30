# Adding more data

### Adding an MMP module

To add rules for a module already referenced by the ASLRB index (e.g. RB or BR:T), you first need to provide a scanned PDF of the rules, named `ASL Rulebook (xxx).pdf`.

Then, write a targets file `ASL Rulebook (xxx).targets`, that describes where each rule lives within the PDF. As an example, take a look at the `ASL Rulebook.targets` file that was extracted for you.

*NOTE: Only the page number is required, the X/Y position on the page is optional.*

Finally, bookmarks need to be created in the PDF for each rule, so that the program can jump directly to each rule:
```
    asl_rulebook2/bin/prepare_pdf.py \
        xxx-original.pdf \
        --targets targets.json \
        --yoffset 5 \
        --output /tmp/xxx-prepared.pdf
```
Save the prepared file as `ASL Rulebook (xxx).pdf`, and the targets file, in your data directory, and restart the server.

Optionally, you can also provide:
- a `ASL Rulebook (xxx).chapters` file (to be able to browse the PDF in the *Chapters* panel)
- a `ASL Rulebook (xxx).footnotes` file (if the rules have any footnotes).

To add a chapter icon and background, create files `XXX-icon.png` and `XXX-background.png`, where `XXX` is the chapter ID. For MMP modules, this is inferred from the rule ID (e.g. "O3.3" becomes "O"); for third-party modules, you can define a chapter ID by adding a `chapter_id` key to the `.chapters` files.

### Adding a third-party module

To add rules for a module not already referenced by the ASLRB index, the process is the same as above, but you also need to write a `.index` file. As an example, take a look at the `ASL Rulebook.index` file that was extracted for you.

All the files should have the same base filename e.g.
- kgs.index
- kgs.pdf
- kgs.targets
- etc...

### Adding Q+A, errata, user annoations, ASOP

This is described [here](../asl_rulebook2/webapp/tests/fixtures/full/).

*NOTE: If you add Q+A, there is a tool in `$/asl_rulebook2/bin/qa-helper/` to help with the process.*