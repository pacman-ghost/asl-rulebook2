import { gMainApp, gFootnoteIndex, gEventBus, gUrlParams } from "./MainApp.js" ;
import { findTargets, showErrorMsg, showNotificationMsg, hideFootnotes } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "content-pane", {

    props: [ "contentDocs" ],

    template: `
<div>
    <tabbed-pages tabbedPagesId="content" ref="tabbedPages">
        <tabbed-page v-for="cdoc in contentDocs" :tabId=cdoc.cdoc_id :caption=cdoc.title :key=cdoc.cdoc_id >
            <content-doc :cdoc=cdoc />
        </tabbed-page>
    </tabbed-pages>
    <asop />
</div>`,

    created() {

        gEventBus.on( "show-target", (cdocId, ruleid) => {
            // check if the target has footnote(s) associated with it
            if ( gFootnoteIndex[ cdocId ] ) {
                let footnotes = gFootnoteIndex[ cdocId ][ ruleid ] ;
                if ( footnotes ) {
                    // yup - show them to the user
                    this.showFootnotes( footnotes ) ;
                }
            }
        } ) ;

    },

    mounted() {
        const showContentDoc = (cdocId) => {
            this.$refs.tabbedPages.activateTab( cdocId ) ; // nb: tabId == cdocId
        }
        gEventBus.on( "show-target", (cdocId, ruleid) => { //eslint-disable-line no-unused-vars
            showContentDoc( cdocId ) ;
        } ) ;
        gEventBus.on( "show-page", (cdocId, pageNo) => { //eslint-disable-line no-unused-vars
            showContentDoc( cdocId ) ;
        } ) ;
    },

    methods: {

        showFootnotes( footnotes ) {

            // quickly hide the footnote balloon if it's already showing
            // NOTE: It would be nice to leave it where it is if it's the same footnote, but we would
            // also need to stop the show-target handler from closing it, and it becomes more effort
            // than it's worth for something that will happen rarely.
            hideFootnotes( true ) ;

            // show the footnote in a notification balloon
            let msg = this.makeFootnoteContent( footnotes ) ;
            let $growl = showNotificationMsg( "footnote", msg ) ;
            if ( ! $growl ) {
                // NOTE: We get here when running the test suite (notifications are stored in a message buffer).
                return ;
            }

            // adjust the width of the balloon (based on the available width)
            // NOTE: The longest footnote is ~7K (A25.8), so we try to hit the max width at ~3K.
            let $contentPane = $( this.$el ) ;
            let width = Math.min( 50 + 30 * (msg.length / 3000), 80 ) ;
            width *= $contentPane.width() / 100 ;
            $growl.css( "width", Math.floor(width)+"px" ) ;

            // FUDGE! We want to limit how tall the notification balloon can get, and show a v-scrollbar
            // for the content if there's too much. However, max-height only works if one of the parent elements
            // has a specific height set for it, so we set a timer to configure the height of the balloon
            // to whatever it is after it has appeared on-screen. Sigh...
            setTimeout( () => {
                let height = $growl.height() ;
                let maxHeight = $contentPane.height() * 0.4 ; // nb: CSS max-height of #growls-br is 40%
                if ( height > maxHeight )
                    height = maxHeight - 40 ;
                // FIXME! This is really jerky, but I can't get it to animate :-/ But it's only a problem
                // when the v-scrollbar comes into play, and there's stuff moving around as that happens,
                // so it's a bit less visually annoying. The footnote balloons are on a light background,
                // which also helps.
                $growl.css( "height", Math.floor(height)+"px" ) ;
            }, 500 ) ; // nb: yes, this needs to be this large :-/
        },

        makeFootnoteContent( footnotes ) {

            let buf = [] ;
            function addCaption( footnote, caption, style ) {
                buf.push( "<div class='header' ", style ? "style='"+style+"'" : "", ">",
                    "<span class='caption'>", caption.caption, " ("+caption.ruleid+")", "</span>", " ",
                    "<span class='footnote-id'>", "["+footnote.display_name+"]", "</span>",
                "</div>" ) ;
            }

            if ( footnotes.length == 1 ) {
                // there is only 1 footnote - we make only its content v-scrollable
                let footnote = footnotes[0] ;
                buf.push( "<div class='footnote'>" ) ;
                footnote.captions.forEach( (caption) => {
                    addCaption( footnote, caption, "padding: 0 5px;" ) ;
                } ) ;
                buf.push( "<div class='content'>", footnote.content, "</div>" ) ;
                buf.push( "</div>" ) ;
            } else {
                // there are multiple footnotes - we make the entire content scrollable
                buf.push( "<div class='content'>" ) ;
                footnotes.forEach( (footnote) => {
                    buf.push( "<div class='footnote'>" ) ;
                    footnote.captions.forEach( (caption) => {
                        addCaption( footnote, caption ) ;
                    } ) ;
                    buf.push( footnote.content ) ;
                    buf.push( "</div>" ) ;
                } ) ;
                buf.push( "</div>" ) ;
            }

            return buf.join( "" ) ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "content-doc", {

    props: [ "cdoc" ],
    data() { return {
        ruleid: null, pageNo: null,
        noContent: gUrlParams.get( "no-content" ),
    } ; },

    template: `
<div class="content-doc" :data-ruleid=ruleid >
    <div v-if=noContent class="disabled">
        <div style='margin-bottom:0.25em;'>&mdash;&mdash;&mdash; Content disabled &mdash;&mdash;&mdash; </div>
        {{cdoc.title}}
        <div v-if=ruleid> ruleid = {{ruleid}} </div>
        <div v-else-if=pageNo> page = {{pageNo}} </div>
    </div>
    <iframe v-else-if=cdoc.url :src=makeDocUrl />
    <div v-else class="disabled"> No content. </div>
</div>`,

    created() {

        gEventBus.on( "show-target", (cdocId, ruleid) => {
            if ( cdocId != this.cdoc.cdoc_id || !ruleid )
                return ;
            let targets = findTargets( ruleid, this.cdoc.parent_cset_id ) ;
            if ( ! targets || targets.length == 0 ) {
                showErrorMsg( "Unknown ruleid: " + ruleid ) ;
                return ;
            }
            // scroll to the specified ruleid
            // FUDGE! We give the tab time to show itself before we scroll to the ruleid.
            setTimeout( () => {
                this.ruleid = ruleid ;
                this.pageNo = null ;
            }, 50 ) ;
        } ) ;

        gEventBus.on( "show-page", (cdocId, pageNo) => {
            if ( cdocId != this.cdoc.cdoc_id )
                return ;
            // scroll to the specified page
            // FUDGE! We give the tab time to show itself before we scroll to the page.
            setTimeout( () => {
                this.pageNo = pageNo ;
                this.ruleid = null ;
            }, 50 ) ;
        } ) ;

    },

    computed: {

        makeDocUrl() {
            let url = this.cdoc.url ;
            if ( this.ruleid )
                url += "#nameddest=" + this.ruleid ;
            else if ( this.pageNo )
                url += "#page=" + this.pageNo ;
            return url ;
        }

    },

} ) ;
