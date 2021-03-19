import { gMainApp, gContentDocs, gEventBus } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane", {

    template: `
<tabbed-pages>
    <tabbed-page tabId="search" caption="Search" >
        <nav-pane-search />
    </tabbed-page>
    <tabbed-page tabId="chapters" caption="Chapters" >
        <nav-pane-chapters />
    </tabbed-page>
</tabbed-pages>`,

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane-search", {

    data() { return {
        seqNo: 0, // nb: for the test suite
    } ; },

    template: `
<search-box id="search-box" @search=onSearch />
<search-results id="search-results" :data-seqno=seqNo />
`,

    created() {
        gEventBus.on( "search-done", () => {
            // notify the test suite that the search results are now available
            this.seqNo += 1 ;
        } ) ;
    },

    methods: {
        onSearch( queryString ) {
            // run the search (handled elsewhere)
            gEventBus.emit( "search", queryString ) ;
        },
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane-chapters", {

    data() { return {
        chapters: [],
    } ; },

    template: `
<accordian>
    <accordian-pane v-if="chapters.length > 0" v-for="c in chapters"
      :key=c :paneKey=c[0] :entries=c[1].sections
      :title=c[1].title :iconUrl=c[1].icon :backgroundUrl=c[1].background
      @pane-expanded=onChapterPaneExpanded(c[0],c[1])
      @entry-clicked=onChapterSectionClicked
    />
    <div v-else class="no-chapters"> No chapters. </div>
</accordian>
`,

    created() {
        // initialize the chapters
        gEventBus.on( "app-loaded", () => {
            Object.values( gContentDocs ).forEach( (cdoc) => {
                if ( ! cdoc.chapters )
                    return ;
                cdoc.chapters.forEach( (chapter) => {
                    this.chapters.push( [ cdoc.cdoc_id, chapter ] ) ;
                } ) ;
            } ) ;
        } ) ;
    },

    methods: {
        onChapterPaneExpanded( cdocId, chapter ) {
            // show the first page of the specified chapter
            gEventBus.emit( "show-page", cdocId, chapter.page_no ) ;
        },
        onChapterSectionClicked( cdocId, entry ) {
            // show the chapter section's target
            gEventBus.emit( "show-target", cdocId, entry.ruleid ) ;
        },
    },

} ) ;
