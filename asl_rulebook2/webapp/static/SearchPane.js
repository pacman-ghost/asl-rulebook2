import { gMainApp, gEventBus } from "./MainApp.js" ;
import { findTargets, getPrimaryTarget, fixupSearchHilites } from "./utils.js" ;

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
    <button @click="$emit('search',this.queryString)" ref="submit"> Go </button>
</div>`,

    mounted: function() {
        // initialize
        $( this.$refs.queryString ).addClass( "ui-widget ui-state-default ui-corner-all" ) ;
        $( this.$refs.submit ).button() ;
    },

    methods: {
        onKeyUp( evt ) {
            if ( evt.keyCode == 13 )
                this.$refs.submit.click() ;
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
<div v-else v-for="sr in searchResults" :key=sr >
    <index-sr v-if="sr.sr_type == 'index'" :sr=sr />
    <qa-entry v-else-if="sr.sr_type == 'q+a'" :qaEntry=sr class="sr" />
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
            let targets = findTargets( queryString, null ) ;
            if ( targets && targets.length > 0 ) {
                // yup - just show it directly (first one, if multiple)
                this.searchResults = null ;
                gEventBus.emit( "show-target", targets[0].cdoc_id, targets[0].target ) ;
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
                if ( resp.error !== undefined ) {
                    onError( resp.error || "Unknown error." ) ;
                    return ;
                }
                // adjust highlighted text
                resp.forEach( this.hiliteSearchResult ) ;
                // load the search results into the UI
                this.$el.scrollTop = 0;
                this.searchResults = resp ;
                // auto-show the primary target for the first search result
                if ( resp.length > 0 && resp[0].sr_type == "index" ) {
                    let target = getPrimaryTarget( resp[0] ) ;
                    if ( target )
                        gEventBus.emit( "show-target", target.cdoc_id, target.target ) ;
                }
                // flag that the search was completed
                onSearchDone() ;
            } ).fail( (xhr, status, errorMsg) => {
                onError( errorMsg ) ;
            } ) ;
        },

        hiliteSearchResult( sr ) {
            // wrap highlighted search terms with HTML span's
            if ( sr.sr_type == "index" ) {
                [ "title", "subtitle", "content" ].forEach( function( key ) {
                    if ( sr[key] !== undefined )
                        sr[key] = fixupSearchHilites( sr[key] ) ;
                } ) ;
            } else if ( sr.sr_type == "q+a" ) {
                if ( ! sr.content )
                    return ;
                sr.content.forEach( (content) => {
                    if ( content.question )
                        content.question = fixupSearchHilites( content.question ) ;
                    if ( content.answers ) {
                        content.answers.forEach( (answer) => {
                            answer[0] = fixupSearchHilites( answer[0] ) ;
                        } ) ;
                    }
                } ) ;
            } else {
                console.log( "INTERNAL ERROR: Unknown search result type:", sr.sr_type ) ;
            }
        },
    },

} ) ;
