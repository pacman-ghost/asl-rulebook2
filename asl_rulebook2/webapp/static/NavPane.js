import { gMainApp, gEventBus } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "nav-pane", {

    template: `
<tabbed-pages>
    <tabbed-page tabId="search" caption="Search" data-display="flex" >
        <search-box id="search-box" @search=onSearch />
        <search-results id="search-results" />
    </tabbed-page>
</tabbed-pages>`,

    methods: {

        onSearch: (queryString) => {
            gEventBus.emit( "search", queryString ) ;
        },

    },

} ) ;
