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

// FUDGE! Can't seem to get access to gMainApp member variables, so we make them available
// to the rest of the program via global variables :-/
export let gAppConfig = null ;
export let gContentDocs = null ;
export let gTargetIndex = null ;
export let gChapterResources = null ;

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
        Promise.all( [
            this.getAppConfig( this ),
            this.getContentDocs( this ),
        ] ).then( () => {
            this.isLoaded = true ;
            gEventBus.emit( "app-loaded" ) ;
            this.showStartupMsgs() ;
            $( "#query-string" ).focus() ; // nb: because autofocus on the <input> doesn't work :-/
        } ).catch( () => {
            // NOTE: Each individual Promise should report their own errors i.e. what could we do here,
            // other than show a generic "startup failed" error?
        } ) ;

        // add a global keypress handler
        $(document).on( "keyup", (evt) => {
            if ( evt.keyCode == 27 ) {
                if ( $(".jquery-image-zoom").length >= 1 )
                    return ; // an image is zoomed - ignore the Escape
                gEventBus.emit( "escape-pressed" ) ;
            }
        } ) ;

    },

    methods: {

        getAppConfig() {
            return new Promise( (resolve, reject) => {
                // get the app config
                $.getJSON( gGetAppConfigUrl, (resp) => { //eslint-disable-line no-undef
                    gAppConfig = resp ;
                    resolve() ;
                } ).fail( (xhr, status, errorMsg) => {
                    let msg = "Couldn't get the app config." ;
                    showErrorMsg( msg + " <div class='pre'>" + errorMsg + "</div>" ) ;
                    reject( msg )
                } ) ;
            } ) ;
        },

        getContentDocs( self ) {
            return new Promise( (resolve, reject) => {
                // get the content docs
                $.getJSON( gGetContentDocsUrl, (resp) => { //eslint-disable-line no-undef
                    if ( gUrlParams.get( "add-empty-doc" ) )
                        resp["empty"] = { "cdoc_id": "empty", "title": "Empty document" } ; // nb: for testing porpoises
                    self.contentDocs = resp ;
                    self.installContentDocs( resp ) ;
                    let cdocIds = Object.keys( resp ) ;
                    if ( cdocIds.length > 0 ) {
                        Vue.nextTick( () => {
                            gEventBus.emit( "show-page", cdocIds[0], 1 ) ; // FIXME! which cdoc do we choose?
                        } ) ;
                    }
                    resolve() ;
                } ).fail( (xhr, status, errorMsg) => {
                    let msg = "Couldn't get the content docs." ;
                    showErrorMsg( msg + " <div class='pre'>" + errorMsg + "</div>" ) ;
                    reject( msg )
                } ) ;
            } ) ;
        },

        installContentDocs( contentDocs ) {
            // install the content docs
            gContentDocs = contentDocs ;
            // build an index of all the targets
            gTargetIndex = {} ;
            Object.values( contentDocs ).forEach( (cdoc) => {
                if ( ! cdoc.targets )
                    return ;
                for ( let ruleid in cdoc.targets ) {
                    let ruleidLC = ruleid.toLowerCase() ;
                    if ( ! gTargetIndex[ ruleidLC ] )
                        gTargetIndex[ ruleidLC ] = [] ;
                    gTargetIndex[ ruleidLC ].push( {
                        cset_id: cdoc.parent_cset_id,
                        cdoc_id: cdoc.cdoc_id,
                        ruleid: ruleid
                    } ) ;
                }
            } ) ;
            // build an index of the available chapters resources
            gChapterResources = { background: {}, icon: {} } ;
            Object.values( contentDocs ).forEach( (cdoc) => {
                if ( ! cdoc.chapters )
                    return ;
                cdoc.chapters.forEach( (chapter) => {
                    if ( "background" in chapter )
                        gChapterResources.background[ chapter.chapter_id ] = chapter.background ;
                    if ( "icon" in chapter )
                        gChapterResources.icon[ chapter.chapter_id ] = chapter.icon ;
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
