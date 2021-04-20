import { gMainApp, gAppConfig, gContentDocs, gEventBus, gUrlParams } from "./MainApp.js" ;
import { getJSON, getURL, linkifyAutoRuleids, getASOPChapterIdFromSectionId, showWarningMsg } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane", {

    props: [ "asop" ],
    data() { return {
        ruleInfo: [],
    } ; },

    template: `
<div>
    <tabbed-pages tabbedPagesId="nav" >
        <tabbed-page tabId="search" image="search" >
            <nav-pane-search />
        </tabbed-page>
        <tabbed-page tabId="chapters" image="chapters" >
            <nav-pane-chapters />
        </tabbed-page>
        <tabbed-page v-if="asop.chapters && asop.chapters.length > 0"
          tabId="asop" image="asop" ref="asop"
        >
            <nav-pane-asop :asop=asop />
        </tabbed-page>
    </tabbed-pages>
    <div id="watermark" />
    <rule-info :ruleInfo=ruleInfo @close=closeRuleInfo />
</div>`,

    created() {

        gEventBus.on( "show-target", (cdocId, ruleid, noRuleInfo) => {
            if ( noRuleInfo || gAppConfig.WEBAPP_DISABLE_AUTO_SHOW_RULE_INFO )
                return ;
            // get the Q+A and annotations for the target being opened
            // NOTE: Targets are associated with a content set, but the Q+A is global, which is not quite
            // the right thing to do - what if there is a ruleid that exists in multiple content set,
            // but is referenced in the Q+A? Hopefully, this will never happen... :-/
            let url = gGetRuleInfoUrl.replace( "RULEID", ruleid ) ; //eslint-disable-line no-undef
            getJSON( url ).then( (resp) => {
                if ( resp.length > 0 ) {
                    // install the rule info entries
                    this.ruleInfo = resp ;
                }
            } ).catch( (errorMsg) => {
                showWarningMsg( "Couldn't get the Q+A for " + ruleid + ".", errorMsg ) ;
            } ) ;
        } ) ;

    },

    methods: {
        closeRuleInfo() {
            // close the rule info popup
            let isOpen = this.ruleInfo.length > 0 ;
            this.ruleInfo = [] ;
            return isOpen ;
        },
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane-search", {

    data() { return {
        seqNo: 0, // nb: for the test suite
        show: gUrlParams.get( "no-animations" ),
    } ; },

    template: `
<search-box :style="{display: show ? 'block' : 'none'}" @search=onSearch
    id="search-box" ref="searchBox"
/>
<search-results :data-seqno=seqNo id="search-results" />
`,

    created() {
        // NOTE: We can sometimes see the search box being built during startup (as the background images
        // are loaded), so we start it off hidden, and fade it in after the webapp has initialized.
        gEventBus.on( "app-loaded", () => {
            if ( ! this.show ) {
                $( this.$refs.searchBox.$el ).fadeIn( 500, () => {
                    this.show = true ;
                } ) ;
            }
        } ) ;
        // notify the test suite that the search results are now available
        gEventBus.on( "search-done", () => {
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
<accordian accordianId="chapters" >
    <accordian-pane v-if="chapters.length > 0" v-for="c in chapters"
      :key=c :paneKey=c
      :entries=c[1].sections :getEntryKey=getEntryKey
      :title=c[1].title :iconUrl=c[1].icon :backgroundUrl=c[1].background :borderClass=makeBorderClass(c)
      @pane-expanded=onChapterPaneExpanded
      @entry-clicked=onChapterEntryClicked
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

        onChapterPaneExpanded( chapter, isClick ) { //eslint-disable-line no-unused-vars
            // show the first page of the specified chapter
            gEventBus.emit( "show-page", chapter[0], chapter[1].page_no ) ;
        },

        onChapterEntryClicked( paneKey, entry ) {
            // show the chapter entry's target
            if ( entry.ruleid )
                gEventBus.emit( "show-target", paneKey[0], entry.ruleid, true ) ;
            else if ( entry.page_no )
                gEventBus.emit( "show-page", paneKey[0], entry.page_no, true ) ;
            else
                console.log( "ERROR: Don't know how to show chapter section:", entry ) ;

        },

        getEntryKey( entry ) { return entry.ruleid || entry.page_no ; },
        makeBorderClass( chapter ) { return chapter[1].chapter_id ? "chapter-" + chapter[1].chapter_id.toLowerCase() : null ; },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane-asop", {

    props: [ "asop" ],
    data() { return {
        footer: null,
    } ; },

    template: `
<accordian accordianId="asop" >
    <accordian-pane v-if="asop.chapters.length > 0" v-for="c in asop.chapters"
      :key=c :paneKey=c :data-chapterid=c.chapter_id
      :entries=c.sections :getEntryKey=getEntryKey
      :title=c.caption
      @pane-expanded=onPaneExpanded @entry-clicked=onEntryClicked
    />
</accordian>
<div v-show=footer v-html=footer id="asop-footer" ref="footer" />
`,

    created() {

        // get the ASOP footer
        gEventBus.on( "app-loaded", () => {
            getURL( gGetASOPFooterUrl ).then( (resp) => { //eslint-disable-line no-undef
                this.footer = resp ;
                this.$nextTick( () => {
                    linkifyAutoRuleids( $( this.$refs.footer ) ) ;
                } ) ;
            } ).catch( (errorMsg) => {
                console.log( "Couldn't get the ASOP footer: " + errorMsg ) ;
            } ) ;
        } ) ;

        // open the appropriate chapter pane when the user clicks on an ASOP section search result
        gEventBus.on( "show-asop-entry-sr", (sectionId, content) => { //eslint-disable-line no-unused-vars
            let chapterId = getASOPChapterIdFromSectionId( sectionId ) ;
            this.asop.chapters.forEach( (chapter) => {
                if ( chapter.chapter_id == chapterId )
                    gEventBus.emit( "expand-pane", "asop", chapter ) ;
            } ) ;
        } ) ;

    },

    methods: {

        // NOTE: We forward events to the ASOP popup for processing.
        onPaneExpanded( chapter, isClick ) { gEventBus.emit( "asop-chapter-expanded", chapter, isClick ) ; },
        onEntryClicked( chapter, section  ) { gEventBus.emit( "show-asop-section", chapter, section ) ; },

        getEntryKey( section ) { return section.section_id ; },

    },

} ) ;
