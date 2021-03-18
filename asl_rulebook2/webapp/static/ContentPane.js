import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;

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
        gEventBus.on( "show-target", (cdocId, target) => { //eslint-disable-line no-unused-vars
            this.$refs.tabbedPages.activateTab( cdocId ) ; // nb: tabId == cdocId
        } ) ;
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "content-doc", {

    props: [ "cdoc" ],
    data() { return {
        target: null,
        noContent: gUrlParams.get( "no-content" ),
    } ; },

    template: `
<div class="content-doc" :data-target=target >
    <div v-if=noContent class="disabled">
        <div style='margin-bottom:0.25em;'>&mdash;&mdash;&mdash; Content disabled &mdash;&mdash;&mdash; </div>
        {{cdoc.title}} <div v-if=target> target = {{target}} </div>
    </div>
    <iframe v-else-if=cdoc.url :src=makeDocUrl />
    <div v-else class="disabled"> No content. </div>
</div>`,

    created() {
        gEventBus.on( "show-target", (cdocId, target) => {
            if ( cdocId != this.cdoc.cdoc_id )
                return ;
            // FUDGE! We give the tab time to show itself before we scroll to the target.
            setTimeout( () => {
                this.target = target ;
            }, 50 ) ;
        } ) ;
    },

    computed: {

        makeDocUrl() {
            let url = this.cdoc.url ;
            if ( this.target )
                url += "#nameddest=" + this.target ;
            return url ;
        }

    },

} ) ;
