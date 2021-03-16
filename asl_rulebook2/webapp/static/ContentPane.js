import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "content-pane", {

    props: [ "contentDocs" ],

    template: `
<tabbed-pages ref="tabbedPages">
    <tabbed-page v-for="doc in contentDocs" :tabId=doc.doc_id :caption=doc.title :key=doc.doc_id >
        <content-doc :doc=doc />
    </tabbed-page>
</tabbed-pages>`,

    mounted() {
        gEventBus.on( "show-target", (docId, target) => { //eslint-disable-line no-unused-vars
            this.$refs.tabbedPages.activateTab( docId ) ; // nb: tabId == docId
        } ) ;
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "content-doc", {

    props: [ "doc" ],
    data() { return {
        target: null,
        noContent: gUrlParams.get( "no-content" ),
    } ; },

    template: `
<div class="content-doc" :data-target=target >
    <div v-if=noContent class="disabled"> Content disabled. <div v-if=target>target = {{target}}</div> </div>
    <iframe v-else-if=doc.url :src=makeDocUrl />
    <div v-else class="disabled"> No content. </div>
</div>`,

    created() {
        gEventBus.on( "show-target", (docId, target) => {
            if ( docId != this.doc.doc_id )
                return ;
            // FUDGE! We give the tab time to show itself before we scroll to the target.
            setTimeout( () => {
                this.target = target ;
            }, 50 ) ;
        } ) ;
    },

    computed: {

        makeDocUrl() {
            let url = this.doc.url ;
            if ( this.target )
                url += "#nameddest=" + this.target ;
            return url ;
        }

    },

} ) ;
