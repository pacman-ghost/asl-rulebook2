import { showErrorMsg, showNotificationMsg } from "./utils.js" ;

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

// FUDGE! Can't seem to get access to the content docs via gMainApp, so we make them available
// to the rest of the program via this global variable :-/
export let gContentDocs = null ;

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
            this.showStartupMsgs() ;
            $( "#query-string" ).focus() ; // nb: because autofocus on the <input> doesn't work :-/
        } ) ;
    },

    methods: {

        getContentDocs( self ) {
            return new Promise( (resolve, reject) => {
                // get the content docs
                $.getJSON( gGetContentDocsUrl, (resp) => { //eslint-disable-line no-undef
                    if ( gUrlParams.get( "add-empty-doc" ) )
                        resp["empty"] = { "doc_id": "empty", "title": "Empty document" } ; // nb: for testing porpoises
                    gContentDocs = self.contentDocs = resp ;
                    let docIds = Object.keys( resp ) ;
                    if ( docIds.length > 0 ) {
                        Vue.nextTick( () => {
                            gEventBus.emit( "show-target", docIds[0], null ) ; // FIXME! which one do we choose?
                        } ) ;
                    }
                    resolve() ;
                } ).fail( (xhr, status, errorMsg) => {
                    const msg = "Couldn't get the content docs." ;
                    showErrorMsg( msg + " <div class='pre'>" + errorMsg + "</div>" ) ;
                    reject( msg )
                } ) ;
            } ) ;
        },

        showStartupMsgs() {
            $.getJSON( gGetStartupMsgsUrl, (resp) => { //eslint-disable-line no-undef
                // show any startup messages
                [ "info", "warning", "error" ].forEach( (msgType) => {
                    if ( ! resp[msgType] )
                        return ;
                    resp[msgType].forEach( (msg) => {
                        if ( Array.isArray( msg ) )
                            msg = msg[0] + " <div class='pre'>" + msg[1] + "</div>" ;
                        showNotificationMsg( msgType, msg ) ;
                    } ) ;
                } ) ;
            } ).fail( (xhr, status, errorMsg) => { //eslint-disable-line no-unused-vars
                showErrorMsg( "Couldn't get the startup messages." ) ;
            } ) ;
        },

    },

} ) ;
