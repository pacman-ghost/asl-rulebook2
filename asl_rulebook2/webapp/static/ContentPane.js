import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;
import { findTargets, showErrorMsg } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "content-pane", {

    props: [ "contentDocs" ],

    template: `
<tabbed-pages ref="tabbedPages">
    <tabbed-page v-for="cdoc in contentDocs" :tabId=cdoc.cdoc_id :caption=cdoc.title :key=cdoc.cdoc_id >
        <content-doc :cdoc=cdoc />
    </tabbed-page>
</tabbed-pages>`,

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
