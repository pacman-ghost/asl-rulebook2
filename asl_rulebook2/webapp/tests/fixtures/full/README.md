This directory contains a set of files that demonstrate the full functionality of the program. There is only a minimal amount of content, but there's a little bit of everything, and enough to give you a feel for what the program can do. In particular, there are only a few targets defined, so most of the ruleid's will be greyed out (since the program doesn't know about them).

There are no PDF's provided, so you won't see any real content in the content pane. However, if you have already prepared the MMP eASLRB PDF, copy it into this directory (with the name `ASL Rulebook.pdf`), and everything will automagically work. Alternatively, add `?no-content=1` to the URL when opening the webapp in your browser.

Once you've got the hang of how things work, you can use the files here as a basis to start building the real data files.

### Getting started

The search engine covers:
- any index files (e.g. the `.index` files)
- any Q+A (look in the `q+a/` directory)
- any errata (look in the `errata/` directory)
- any user annotations (defined in the `annotations.json` file)
- most of the ASOP (look in the `asop/` directory)

Take a look through those data files to get a feel for what you can search for.

Run the program, specifying this directory as the data directory e.g.
```
./run-container.sh --port 5020 \
    --data asl_rulebook2/webapp/tests/fixtures/full/ \
    --asop asl_rulebook2/webapp/tests/fixtures/asop/asop/
```

*NOTE: You will see a few things in the UI that might look wrong; this is because this data set is used for testing the program, including error conditions and bad data.*

### Q+A

Search for *"encirclement"*; note how the content PDF has jumped directly to rule A7.7, and the Q+A for that rule have automatically appeared. Click on the image to zoom in. Click on the "close" icon, or press Escape to dismiss the Q+A.

You will see the search results in the left panel, which can be filtered using the checkboxes at the top of the panel.

If you click on the O6.7 rule link, the content pane will switch to showing the *Red Barricades* PDF (if it were there), providing seamless switching between multiple PDF files.

### Errata

Search for *"CCPh"*, and an errata that has been written for rule A3.8 will pop up. Note that it doesn't appear in the search results, because it doesn't contain the word *"CCPh"*. However, if you search for *"errata"*, you will get both the A3.8 index entry (CCPh), and the errata, because they both contain the word *"errata"*.

### User annotations

You can also add your own annotations for a specific rule, defined in the `annotations.json` file.

Search for *"WP"* for an example.

### ASOP

Search for *"CC"* - the last search result will be the 8.21B ASOP step, *"DURING LOCATION's CCPh"*. Click on the titlebar to go to the ASOP entry itself.

You can also just browse through the ASOP, by clicking on the ASOP icon in the bottom-left corner.

### Footnotes

Search for *"error"*. The A.2 rule will come up, and because it has an associated footnote, this will appear in a popup. Hover your mouse over the balloon if you need time to read it.

### Chapters

Finally, if you just want to browse through the rulebook(s), you can quickly jump to major sections withing each chapter by clicking on the *Chapters* icon in the bottom-left corner. Note how *Red Barricades* and *Kampfgruppe Scherer* have been merged in with the main rulebook, to provide a single view of all the configured rulebooks.
