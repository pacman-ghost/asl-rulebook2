import { gMainApp, gAppConfig, gContentDocs, gEventBus } from "./MainApp.js" ;
import { showWarningMsg } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane", {

    data() { return {
        ruleInfo: [],
    } ; },

    template: `
<div>
    <tabbed-pages>
        <tabbed-page tabId="search" caption="Search" >
            <nav-pane-search />
        </tabbed-page>
        <tabbed-page tabId="chapters" caption="Chapters" >
            <nav-pane-chapters />
        </tabbed-page>
    </tabbed-pages>
    <rule-info :ruleInfo=ruleInfo @close=closeRuleInfo />
</div>`,

    created() {

        // show any Q+A and annotations when a target is opened
        gEventBus.on( "show-target", (cdocId, target) => {
            if ( gAppConfig.DISABLE_AUTO_SHOW_RULE_INFO )
                return ;
            // get the rule info for the target being opened
            // NOTE: Targets are associated with a content doc, but the Q+A is global, which is not quite
            // the right thing to do - what if there is a ruleid that is the same multiple content docs,
            // but is referenced in the Q+A? Hopefully, this will never happen... :-/
            let url = gGetRuleInfoUrl.replace( "RULEID", target ) ; //eslint-disable-line no-undef
            $.getJSON( url, (resp) => {
                if ( resp.length > 0 ) {
                    // install the rule info entries
                    this.ruleInfo = resp ;
                }
            } ).fail( (xhr, status, errorMsg) => {
                showWarningMsg( "Couldn't get the Q+A for " + target + ". <div class='pre'>" + errorMsg + "</div>" ) ;
            } ) ;
        } ) ;

        // close the rule info popup if Escape is pressed
        gEventBus.on( "escape-pressed", this.closeRuleInfo ) ;

    },

    methods: {
        closeRuleInfo() {
            // close the rule info popup
            this.ruleInfo = [] ;
        },
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane-search", {

    data() { return {
        seqNo: 0, // nb: for the test suite
    } ; },

    template: `
<search-box id="search-box" @search=onSearch />
<search-results :data-seqno=seqNo id="search-results" />
`,

    created() {
        // notify the test suite that the search results are now available
        gEventBus.on( "search-done", () => {
            this.seqNo += 1 ;
        } ) ;
    },

    methods: {

        onSearch( queryString ) {
            // run the search (handled elsewhere)
            if ( $("#rule-info").css( "display" ) != "none" )
                return ; // nb: dont respond to key-presses if the rule info popup is open
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
