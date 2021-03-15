import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "content-pane", {

    props: [ "contentDocs" ],

    template: `
<tabbed-pages ref="tabbedPages">
    <tabbed-page v-for="doc in contentDocs" :tabId=doc.docId :caption=doc.title >
        <content-doc :doc=doc />
    </tabbed-page>
</tabbed-pages>`,

    mounted() {
        gEventBus.on( "show-content-doc", (docId) => {
            this.$refs.tabbedPages.activateTab( docId ) ; // nb: tabId == docId
        } ) ;
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "content-doc", {

    props: [ "doc" ],
    data() { return {
        noContent: gUrlParams.get( "no-content" ),
    } ; },

    template: `
<div class="content-doc">
    <div v-if=noContent class="disabled"> Content disabled. </div>
    <iframe v-else-if=doc.url :src=doc.url />
    <div v-else class="disabled"> No content. </div>
</div>`,

} ) ;
