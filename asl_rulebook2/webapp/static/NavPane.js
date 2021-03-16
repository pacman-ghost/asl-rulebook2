import { gMainApp, gEventBus } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane", {

    data() { return {
        seqNo: 0, // nb: for the test suite
    } ; },

    template: `
<tabbed-pages>
    <tabbed-page tabId="search" caption="Search" data-display="flex" >
        <search-box id="search-box" @search=onSearch />
        <search-results id="search-results" :data-seqno=seqNo />
    </tabbed-page>
</tabbed-pages>`,

    mounted() {
        gEventBus.on( "search-done", () => {
            // notify the test suite that the search results are now available
            this.seqNo += 1 ;
        } ) ;
    },

    methods: {

        onSearch( queryString ) {
            gEventBus.emit( "search", queryString ) ;
        },

    },

} ) ;
