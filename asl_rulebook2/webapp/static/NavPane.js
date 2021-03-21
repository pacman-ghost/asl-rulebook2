import { gMainApp, gAppConfig, gContentDocs, gEventBus, gUrlParams } from "./MainApp.js" ;
import { showWarningMsg } from "./utils.js" ;

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
        ruleInfo: [],
        seqNo: 0, // nb: for the test suite
        closeRuleInfoImageUrl: gImagesBaseUrl + "cross.png", //eslint-disable-line no-undef
        ruleInfoTransitionName: gUrlParams.get("no-animations") ? "" : "ruleinfo-slide",
    } ; },

    template: `
<search-box id="search-box" @search=onSearch />
<search-results :data-seqno=seqNo id="search-results" />
<!-- FUDGE! We want the "close" button to stay in the top-right corner of the rule info popup.
  If we put it inside the <rule-info> element with an absolute position, it scrolls with the content,
  so we place it outside the <rule-info> element, with an absolute position, and a larger z-index.
  It doesn't look so good when the v-scrollbar appears, but we can live with that.
-->
<transition :name=ruleInfoTransitionName @after-enter=onAfterEnterRuleInfoTransition >
    <div v-show="ruleInfo.length > 0" >
        <img :src=closeRuleInfoImageUrl @click=closeRuleInfo ref="closeRuleInfoButton"
          title="Close the rule info" class="close-rule-info"
        />
        <rule-info :ruleInfo=ruleInfo ref="rule-info" />
    </div>
</transition>
`,

    created() {

        // notify the test suite that the search results are now available
        gEventBus.on( "search-done", () => {
            this.seqNo += 1 ;
        } ) ;

        // show any Q+A when a target is opened
        gEventBus.on( "show-target", (cdocId, target) => {
            if ( gAppConfig.DISABLE_AUTO_SHOW_RULE_INFO )
                return ;
            // get the Q+A and annotations for the target being opened
            // NOTE: Targets are associated with a content doc, but the Q+A is global, which is not quite
            // the right thing to do - what if there is a ruleid that is the same multiple content docs,
            // but is referenced in the Q+A? Hopefully, this will never happen... :-/
            let url = gGetRuleInfoUrl.replace( "RULEID", target ) ; //eslint-disable-line no-undef
            $.getJSON( url, (resp) => {
                if ( resp.length > 0 )
                    this.showRuleInfo( resp ) ;
            } ).fail( (xhr, status, errorMsg) => {
                showWarningMsg( "Couldn't get the Q+A for " + target + ". <div class='pre'>" + errorMsg + "</div>" ) ;
            } ) ;
        } ) ;

        // close the rule info popup if Escape is pressed
        gEventBus.on( "escape-pressed", this.closeRuleInfo ) ;

    },

    methods: {

        onSearch( queryString ) {
            // run the search (handled elsewhere)
            if ( this.ruleInfo.length > 0 )
                return ; // nb: dont respond to key-presses if the rule info popup is open
            gEventBus.emit( "search", queryString ) ;
        },

        showRuleInfo( ruleInfo ) {
            // install the rule info entries
            this.ruleInfo = ruleInfo ;
            $( this.$refs.closeRuleInfoButton ).hide() ;
        },
        closeRuleInfo() {
            // close the rule info popup
            this.ruleInfo = [] ;
        },
        onAfterEnterRuleInfoTransition() {
            // FUDGE! We have to wait until the rule info popup is open before we can check
            // if it has a v-scrollbar or not, and hence where we should put the close button.
            this.$nextTick( () => {
                let ruleInfo = this.$refs[ "rule-info" ].$el ;
                let closeButton = this.$refs.closeRuleInfoButton ;
                if ( ruleInfo.clientHeight >= ruleInfo.scrollHeight )
                    $(closeButton).css( "right", "6px" ) ;
                else {
                    // FUDGE! The v-scrollbar is visible, so we move the "close" button left a bit.
                    // This adjustment won't update if the pane is resized, but we can live with that.
                    $(closeButton).css( "right", "18px" ) ;
                }
                $(closeButton).fadeIn( 200 ) ;
            } ) ;
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
