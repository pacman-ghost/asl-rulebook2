import { gMainApp, gEventBus } from "./MainApp.js" ;
import { IndexSearchResult } from "./SearchResult.js" ;

// --------------------------------------------------------------------

gMainApp.component( "search-panel", {

    template: "<search-box /> <search-results />",

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "search-box", {

    data: function() { return {
        queryString: "",
    } ; },

    template: `
<div>
    <input type="text" id="query-string" @keyup=onKeyUp v-model.trim="queryString" ref="queryString" autofocus >
    <button @click="$emit('search',this.queryString)" ref=submit> Go </button>
</div>`,

    mounted: function() {
        // initialize
        $( this.$refs.queryString ).addClass( "ui-widget ui-state-default ui-corner-all" ) ;
        $( this.$refs.submit ).button() ;
    },

    methods: {
        onKeyUp: function( evt ) {
            if ( evt.keyCode == 13 )
                this.$refs["submit"].click() ;
        }
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "search-results", {

    data() { return {
        searchResults: [],
    } ; },

    template: `<div>
<div v-for="sr in searchResults" :key=sr.key >
    <index-sr v-if="sr.srType == 'index'" :sr=sr />
    <div v-else> ??? </div>
</div>
</div>`,

    mounted() {
        gEventBus.on( "search", this.onSearch ) ;
    },

    methods: {

        onSearch( queryString ) {
            // generate some dummy search results
            let searchResults = [] ;
            for ( let i=0 ; i < queryString.length ; ++i ) {
                let buf = [ "Search result #" + (1+i) ] ;
                let nItems = Math.floor( Math.sqrt( 100 * Math.random() ) ) - 1 ;
                if ( nItems > 0 ) {
                    buf.push( "<ul style='padding-left:1em;'>" ) ;
                    for ( let j=0 ; j < nItems ; ++j )
                        buf.push( "<li> item " + (1+j) ) ;
                    buf.push( "</ul>" ) ;
                }
                searchResults.push(
                    new IndexSearchResult( i, buf.join("") )
                ) ;
            }
            this.searchResults = searchResults ;
        },

    },

} ) ;
