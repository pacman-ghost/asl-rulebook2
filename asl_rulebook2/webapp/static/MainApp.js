import { showErrorMsg } from "./utils.js" ;

// parse any URL parameters
export let gUrlParams = new URLSearchParams( window.location.search.substring(1) ) ;

// create the main application
export const gMainApp = Vue.createApp( { //eslint-disable-line no-undef
    template: "<main-app />",
} ) ;
export const gEventBus = new TinyEmitter() ; //eslint-disable-line no-undef
$(document).ready( () => {
    gMainApp.mount( "#main-app" ) ;
} ) ;

// --------------------------------------------------------------------

gMainApp.component( "main-app", {

    data() { return {
        contentDocs: [],
        isLoaded: false,
    } ; },

    template: `
<nav-pane id="nav" />
<content-pane id="content" :contentDocs=contentDocs />
<div v-if=isLoaded id="_mainapp-loaded_" />
`,

    mounted() {
        // initialize the splitter
        Split( [ "#nav", "#content" ], { //eslint-disable-line no-undef
            direction: "horizontal",
            sizes: [ 25, 75 ],
            gutterSize: 2,
        } ) ;
        // initialze the webapp
        // NOTE: We don't provide a catch handler, since each individual Promise should report
        // their own errors i.e. what could we do here, other than show a generic "startup failed" error?
        Promise.all( [
            this.getContentDocs( this ),
        ] ).then( () => {
            this.isLoaded = true ;
            $( "#query-string" ).focus() ; // nb: because autofocus on the <input> doesn't work :-/
        } ) ;
    },

    methods: {

        getContentDocs: (self) => new Promise( (resolve, reject) => {
            // get the content docs
            $.getJSON( gGetContentDocsUrl, (resp) => { //eslint-disable-line no-undef
                self.contentDocs = resp ;
                let docIds = Object.keys( resp ) ;
                if ( docIds.length > 0 ) {
                    Vue.nextTick( () => {
                        gEventBus.emit( "show-content-doc", docIds[0] ) ; // FIXME! which one do we choose?
                    } ) ;
                }
                resolve() ;
            } ).fail( (xhr, status, errorMsg) => {
                const msg = "Couldn't get the content docs." ;
                showErrorMsg( msg + " <div class='pre'>" + errorMsg + "</div>" ) ;
                reject( msg )
            } ) ;
        } ),

    },

} ) ;
