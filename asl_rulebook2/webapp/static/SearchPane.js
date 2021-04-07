import { gMainApp, gAppConfig, gEventBus } from "./MainApp.js" ;
import { gUserSettings, saveUserSettings } from "./UserSettings.js" ;
import { postURL, findTargets, getPrimaryTarget, linkifyAutoRuleids, fixupSearchHilites, hideFootnotes } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "search-panel", {

    template: "<search-box /> <search-results />",

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "search-box", {

    data: function() { return {
        queryString: "",
        srCount: null, srCountInfo: null, showSrCount: false,
    } ; },

    template: `
<div>
    <div class="row">
        <input type="text" id="query-string" @keyup=onKeyUp v-model.trim="queryString" ref="queryString" autofocus >
        <button @click="$emit('search',this.queryString)" ref="submit"> Go </button>
    </div>
    <div class="row sr-filters" style="display:none;" ref="srFilters" >
        <b> Show: </b>
        <input type="checkbox" name="show-index-sr" @click=onClickSrFilter > <label for="show-index-sr"> Index </label>
        <input type="checkbox" name="show-qa-sr" @click=onClickSrFilter > <label for="show-qa-sr"> Q+A </label>
        <input type="checkbox" name="show-errata-sr" @click=onClickSrFilter > <label for="show-errata-sr"> Errata </label>
        <input type="checkbox" name="show-asop-entry-sr" @click=onClickSrFilter > <label for="show-asop-entry-sr"> ASOP </label>
        <span v-if=showSrCount :title=srCountInfo class="sr-count"> {{srCount}} </span>
    </div>
</div>`,

    created() {

        gEventBus.on( "app-config-loaded", () => {
            // initialize the search result filter checkboxes
            let nVisible = 0 ;
            $( this.$el ).find( ".sr-filters input[type='checkbox']" ).each( function() {
                // check if the next checkbox will have any effect (e.g. if no Q+A have been configured,
                // then there's no point in showing the checkbox to filter Q+A search results)
                let name = $(this).attr( "name" ) ;
                let match = name.match( /^show-(.+)-sr$/ ) ;
                let key = match[1] ;
                let caps_key = { "index": "content-sets", "asop-entry": "asop" }[ key ] || key ;
                if ( gAppConfig.capabilities[ caps_key ] ) {
                    // yup - load the last-saved state
                    key = "HIDE_" + key.toUpperCase().replace("-","_") + "_SR" ;
                    $(this).prop( "checked", ! gUserSettings[key] ) ;
                    nVisible += 1 ;
                } else {
                    // nope - just hide it
                    $(this).hide() ;
                    $(this).siblings( "label[for='" + name + "']" ).hide() ;
                }
            } ) ;
            if ( nVisible <= 1 ) {
                // there's only 1 checkbox - turn it on and leave everything hidden
                $( this.$el ).find( "input[type='checkbox']" ).prop( "checked", true ) ;
            } else {
                // there are multiple checkboxes - show them to the user
                $( this.$refs.srFilters ).show() ;
            }
        } ) ;

        gEventBus.on( "app-loaded", () => {
            // check if we should start off with a query (for debugging porpoises)
            if ( gAppConfig.INITIAL_QUERY_STRING )
                gEventBus.emit( "search-for", gAppConfig.INITIAL_QUERY_STRING ) ;
        } ) ;

        gEventBus.on( "search-done", (showSrCount) => {
            // a search has been completed - update the search result count
            this.showSrCount = showSrCount ;
            if ( showSrCount )
                this.updateSrCount() ;
        } ) ;

        gEventBus.on( "search-for", (queryString) => {
            // search for the specified query string
            this.queryString = queryString ;
            this.$refs.submit.click() ;
        } ) ;

    },

    mounted: function() {
        // initialize
        $( this.$refs.queryString ).addClass( "ui-widget ui-state-default ui-corner-all" ) ;
        $( this.$refs.submit ).button() ;
    },

    methods: {

        onClickSrFilter( evt ) {
            // a search result filter checkbox was clicked - update the user settings
            let match = evt.target.getAttribute( "name" ).match( /^show-(.+)-sr$/ ) ;
            let srType = match[1] ;
            let state = evt.target.checked ;
            gUserSettings[ "HIDE_" + srType.toUpperCase().replace("-","_") + "_SR" ] = ! state ;
            saveUserSettings() ;
            // hide/show the corresponding search results
            let $elem = $( "#search-results .sr[data-srtype='" + srType + "']" ) ;
            $elem.css( "display", state ? "block" : "none" ) ;
            this.updateSrCount() ;
        },

        updateSrCount() {
            // show the number of hidden/visible search results
            if ( ! this.showSrCount )
                return ;
            let nVisible=0, nTotal=0 ;
            $( "#search-results .sr" ).each( function() {
                nTotal += 1 ;
                if ( $(this).css( "display" ) != "none" )
                    nVisible += 1 ;
            } ) ;
            if ( nVisible == 0 && nTotal == 0 ) {
                this.srCount = null ;
                this.srCountInfo = null ;
            } else {
                this.srCount = nVisible + "/" + nTotal ;
                if ( nVisible == 0 && nTotal == 1 )
                    this.srCountInfo = "Not showing the 1 search result" ;
                else if ( nVisible == 1 && nTotal == 1 )
                    this.srCountInfo = "Showing the 1 search result" ;
                else
                    this.srCountInfo = "Showing " + nVisible + " of " + nTotal + " search results" ;
            }
            gEventBus.emit( "sr-filtered", nVisible, nTotal ) ;
        },

        onKeyUp( evt ) {
            if ( evt.keyCode == 13 )
                this.$refs.submit.click() ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "search-results", {

    data() { return {
        searchResults: null,
        errorMsg: null,
        noResultsMsg: null,
    } ; },

    template: `<div>
<div v-if=errorMsg class="error"> Search error: <div class="pre"> {{errorMsg}} </div> </div>
<div v-else>
    <div v-if=noResultsMsg class="no-results"> {{noResultsMsg}} </div>
    <div v-for="sr in searchResults" :key=sr >
        <index-sr v-if="sr.sr_type == 'index'" :sr=sr data-srtype="index"
            :style="{ display: showSr(sr.sr_type) ? 'block' : 'none' }"
            class="sr"
        />
        <qa-entry v-else-if="sr.sr_type == 'qa'" :qaEntry=sr data-srtype="qa"
            :style="{ display: showSr(sr.sr_type) ? 'block' : 'none' }"
            class="sr"
        />
        <annotation v-else-if="sr.sr_type == 'errata'" :anno=sr data-srtype="errata"
            :style="{ display: showSr(sr.sr_type) ? 'block' : 'none' }"
            class="sr"
        />
        <annotation v-else-if="sr.sr_type == 'user-anno'" :anno=sr class="sr rule-info" />
        <asop-entry-sr v-else-if="sr.sr_type == 'asop-entry'" :sr=sr data-srtype="asop-entry"
            :style="{ display: showSr(sr.sr_type) ? 'block' : 'none' }"
            class="sr"
        />
        <div v-else> ???:{{sr.sr_type}} </div>
    </div>
</div>
</div>`,

    mounted() {

        // handle requests to do a search
        gEventBus.on( "search", this.onSearch ) ;

        // update after search result filtering has been changed
        gEventBus.on( "sr-filtered", (nVisible, nTotal) => {
            if ( nTotal == 0 )
                this.noResultsMsg = "Nothing was found." ;
            else if ( nVisible == 0 )
                this.noResultsMsg = "All search results have been filtered." ;
            else
                this.noResultsMsg = null ;
        } ) ;

    },

    updated() {
        // make the ruleid's clickable
        linkifyAutoRuleids( $( this.$el ) ) ;
    },

    methods: {

        onSearch( queryString ) {

            // initialize
            this.errorMsg = null ;
            this.noResultsMsg = null ;
            hideFootnotes() ;
            function onSearchDone( showSrCount ) {
                Vue.nextTick( () => { gEventBus.emit( "search-done", showSrCount ) ; } ) ;
            }

            // check if the query string is just a ruleid
            let targets = findTargets( queryString, null ) ;
            if ( targets && targets.length > 0 ) {
                // yup - just show it directly (first one, if multiple)
                this.searchResults = null ;
                gEventBus.emit( "show-target", targets[0].cdoc_id, targets[0].ruleid ) ;
                onSearchDone( false ) ;
                return ;
            }

            // submit the search request
            const onError = (errorMsg) => {
                this.errorMsg = errorMsg ;
                onSearchDone( true ) ;
            } ;
            postURL( gSearchUrl, //eslint-disable-line no-undef
                { queryString: queryString }
            ).then( (resp) => {
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
                        gEventBus.emit( "show-target", target.cdoc_id, target.ruleid ) ;
                }
                // flag that the search was completed
                onSearchDone( true ) ;
            } ).catch( (errorMsg) => {
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
            } else if ( sr.sr_type == "qa" ) {
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
            } else if ( sr.sr_type == "errata" || sr.sr_type == "user-anno" ) {
                sr.content = fixupSearchHilites( sr.content ) ;
            } else if ( sr.sr_type == "asop-entry" ) {
                sr.content = fixupSearchHilites( sr.content ) ;
            } else {
                console.log( "INTERNAL ERROR: Unknown search result type:", sr.sr_type ) ;
            }
        },

        showSr( srType ) {
            // figure out if a search result should start off hidden or visible
            let name = "show-" + srType + "-sr" ;
            let $elem = $( "#search-box input[type='checkbox'][name='" + name + "']" ) ;
            let state = $elem.prop( "checked" ) ;
            return state ;
        },

    },

} ) ;
