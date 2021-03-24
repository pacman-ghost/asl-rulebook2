import { getJSON, showErrorMsg, showNotificationMsg } from "./utils.js" ;

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
export let gFootnoteIndex = null ;
export let gChapterResources = null ;
export let gASOPChapterIndex = null ;
export let gASOPSectionIndex = null ;

// --------------------------------------------------------------------

gMainApp.component( "main-app", {

    data() { return {
        contentDocs: [],
        asop: {},
        isLoaded: false,
    } ; },

    template: `
<nav-pane id="nav" :asop=asop ref="navPane" />
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
            this.getAppConfig(),
            this.getContentDocs( this ),
            this.getFootnoteIndex(),
            this.getASOP(),
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
            if ( evt.keyCode == 27 )
                this.onEscapePressed() ;
        } ) ;

    },

    methods: {

        getAppConfig() {
            // get the app config
            return getJSON( gGetAppConfigUrl ).then( (resp) => { //eslint-disable-line no-undef
                gAppConfig = resp ;
            } ).catch( (errorMsg) => {
                showErrorMsg( "Couldn't get the app config.", errorMsg ) ;
            } ) ;
        },

        getContentDocs( self ) {
            // get the content docs
            return getJSON( gGetContentDocsUrl ).then( (resp) => { //eslint-disable-line no-undef
                // install the content docs
                if ( gUrlParams.get( "add-empty-doc" ) )
                    resp["empty"] = { "cdoc_id": "empty", "title": "Empty document" } ; // nb: for testing porpoises
                self.contentDocs = resp ;
                self.installContentDocs( resp ) ;
                // start off showing the first content doc
                let cdocIds = Object.keys( resp ) ;
                if ( cdocIds.length > 0 ) {
                    Vue.nextTick( () => {
                        gEventBus.emit( "show-page", cdocIds[0], 1 ) ; // FIXME! which cdoc do we choose?
                    } ) ;
                }
            } ).catch( (errorMsg) => {
                showErrorMsg( "Couldn't get the content docs.", errorMsg ) ;
            } ) ;
        },

        getFootnoteIndex() {
            // get the footnotes
            return getJSON( gGetFootnotesUrl ).then( (resp) => { //eslint-disable-line no-undef
                gFootnoteIndex = resp ;
            } ).catch( (errorMsg) => {
                showErrorMsg( "Couldn't get the footnote index.", errorMsg ) ;
            } ) ;
        },

        getASOP() {
            // get the ASOP
            return getJSON( gGetASOPUrl ).then( (resp) => { //eslint-disable-line no-undef
                this.asop = resp ;
                // build an index of the ASOP chapters and sections
                gASOPChapterIndex = {} ;
                gASOPSectionIndex = {} ;
                if ( resp.chapters ) {
                    resp.chapters.forEach( (chapter) => {
                        gASOPChapterIndex[ chapter.chapter_id ] = chapter ;
                        if ( chapter.sections ) {
                            chapter.sections.forEach( (section) => {
                                gASOPSectionIndex[ section.section_id ] = section ;
                            } ) ;
                        }
                    } ) ;
                }
            } ).catch( (errorMsg) => {
                showErrorMsg( "Couldn't get the ASOP.", errorMsg ) ;
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
            // show any startup messages
            return getJSON( gGetStartupMsgsUrl ).then( (resp) => { //eslint-disable-line no-undef
                [ "info", "warning", "error" ].forEach( (msgType) => {
                    if ( ! resp[msgType] )
                        return ;
                    resp[msgType].forEach( (msg) => {
                        if ( Array.isArray( msg ) )
                            msg = msg[0] + " <div class='pre'>" + msg[1] + "</div>" ;
                        showNotificationMsg( msgType, msg ) ;
                    } ) ;
                } ) ;
            } ).catch( (errorMsg) => {
                showErrorMsg( "Couldn't get the startup messages.", errorMsg ) ;
            } ) ;
        },

        onEscapePressed() {
            // check if an image is currently zoomed
            if ( $(".jquery-image-zoom").length > 0 ) {
                // yup - no need to do anything (the image will un-zoom itself)
                return ;
            }
            // close any notification balloons
            let isFootnoteOpen = $( ".growl-footnote" ).length > 0 ;
            $( ".growl-close" ).each( function() {
                $(this).trigger( "click" ) ;
            } ) ;
            // check if a footnotes balloon is open
            if ( isFootnoteOpen ) {
                // yup - let it "consume" the Escape key
                return ;
            }
            // check if the rule info popup is open
            if ( this.$refs.navPane.closeRuleInfo() ) {
                // yup - let the Escape close it
                return ;
            }
            // if one of the non-search nav panes are open, switch to the search pane
            gEventBus.emit( "activate-tab", "#nav", "search" ) ;
        },

    },

} ) ;
