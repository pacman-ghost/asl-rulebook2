import { gMainApp, gEventBus } from "./MainApp.js" ;
import { findTarget, fixupSearchHilites } from "./utils.js" ;

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
        onKeyUp( evt ) {
            if ( evt.keyCode == 13 )
                this.$refs["submit"].click() ;
        }
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "search-results", {

    data() { return {
        searchResults: null,
        errorMsg: null,
    } ; },

    template: `<div>
<div v-if=errorMsg class="error"> Search error: <div class="pre"> {{errorMsg}} </div> </div>
<div v-else-if="searchResults != null && searchResults.length == 0" class="no-results"> Nothing was found. </div>
<div v-else v-for="sr in searchResults" :key=sr._key >
    <index-sr v-if="sr.sr_type == 'index'" :sr=sr :key=sr />
    <div v-else> ??? </div>
</div>
</div>`,

    mounted() {
        gEventBus.on( "search", this.onSearch ) ;
    },

    methods: {

        onSearch( queryString ) {

            // initialize
            this.errorMsg = null ;
            function onSearchDone() {
                Vue.nextTick( () => { gEventBus.emit( "search-done" ) ; } ) ;
            }

            // check if the query string is just a target
            let docIds = findTarget( queryString ) ;
            if ( docIds ) {
                // yup - just show it directly
                this.searchResults = null ;
                gEventBus.emit( "show-target", docIds[0][0], docIds[0][1] ) ;
                onSearchDone() ;
                return ;
            }

            // submit the search request
            const onError = (errorMsg) => {
                this.errorMsg = errorMsg ;
                onSearchDone() ;
            } ;
            $.ajax( { url: gSearchUrl, type: "POST", //eslint-disable-line no-undef
                data: { queryString: queryString },
                dataType: "json",
            } ).done( (resp) => {
                // check if there was an error
                if ( resp.error ) {
                    onError( resp.error ) ;
                    return ;
                }
                // adjust highlighted text
                resp.forEach( (sr) => {
                    [ "title", "subtitle", "content" ].forEach( function( key ) {
                        if ( sr[key] )
                            sr[key] = fixupSearchHilites( sr[key] ) ;
                    } ) ;
                } ) ;
                // load the search results into the UI
                this.$el.scrollTop = 0;
                this.searchResults = resp ;
                // auto-show the first related rule we know about
                for ( let i=0 ; i < resp.length ; ++i ) {
                    const ruleids = resp[i].ruleids ;
                    if ( ! ruleids )
                        continue ;
                    const targets = findTarget( ruleids[0] ) ;
                    if ( targets ) {
                        gEventBus.emit( "show-target", targets[0][0], targets[0][1] ) ;
                        break ;
                    }
                }
                // flag that the search was completed
                onSearchDone() ;
            } ).fail( (xhr, status, errorMsg) => {
                onError( errorMsg ) ;
            } ) ;
        },

    },

} ) ;
