import { getJSON, showErrorMsg, showNotificationMsg, hideFootnotes } from "./utils.js" ;

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

    created() {
        gEventBus.on( "show-target", () => {
            hideFootnotes() ;
        } ) ;
    },

    mounted() {

        // initialize the splitter
        Split( [ "#nav", "#content" ], { //eslint-disable-line no-undef
            direction: "horizontal",
            sizes: [ 25, 75 ],
            gutterSize: 2,
        } ) ;

        // initialize hotkeys
        jQuery.hotkeys.options.filterInputAcceptingElements = false ;
        jQuery.hotkeys.options.filterContentEditable = false ;
        jQuery.hotkeys.options.filterTextInputs = false ;
        function selectNav( tabId ) {
            $( "#nav .close-rule-info" ).click() ;
            $( "#nav .tab-strip .tab[data-tabid='" + tabId + "']" ).click() ;
        }
        $( "body" ).bind( "keydown", "alt+r", function( evt ) {
            selectNav( "search" ) ;
            $( "#query-string" ).select() ;
            $( "#query-string" ).focus() ;
            evt.preventDefault() ;
        } ) ;
        $( "body" ).bind( "keydown", "alt+c", function( evt ) { selectNav( "chapters" ) ; evt.preventDefault() ; } ) ;
        $( "body" ).bind( "keydown", "alt+a", function( evt ) { selectNav( "asop" ) ; evt.preventDefault() ; } ) ;

        // initialze the webapp
        Promise.all( [
            this.getAppConfig(),
            this.getContentDocs( this ),
            this.getFootnoteIndex(),
            this.getASOP(),
        ] ).then( () => {
            this.onStartupDone() ;
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
                gEventBus.emit( "app-config-loaded" ) ;
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
            function preloadImage( url ) {
                // FUDGE! If we try to preload the image immediately (even using a Promise), it causes
                // a delay showing the search box background, so we give it a chance to show first.
                setTimeout( () => {
                    // FUDGE! $.get() doesn't do the trick, we have to insert an image element into the DOM :-/
                    let $img = $( "<img src='" + url + "' style='display:none'></img>" ) ;
                    $("body").append( $img ) ;
                }, 200 ) ;
            }
            gChapterResources = { background: {}, icon: {} } ;
            Object.values( contentDocs ).forEach( (cdoc) => {
                if ( ! cdoc.chapters )
                    return ;
                cdoc.chapters.forEach( (chapter) => {
                    if ( "background" in chapter ) {
                        gChapterResources.background[ chapter.chapter_id ] = chapter.background ;
                        preloadImage( chapter.background ) ;
                    }
                    if ( "icon" in chapter ) {
                        gChapterResources.icon[ chapter.chapter_id ] = chapter.icon ;
                        preloadImage( chapter.icon ) ;
                    }
                } ) ;
            } ) ;
        },

        onStartupDone() {
            // show any startup messages
            getJSON( gGetStartupMsgsUrl ).then( (resp) => { //eslint-disable-line no-undef
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
            // check if we should start with a query
            let queryString = gUrlParams.get( "query" ) || gUrlParams.get( "q" ) ;
            if ( window.location.hash != "" )
                queryString = window.location.hash.substring( 1 ) ;
            if ( queryString != null && queryString != undefined ) {
                // yup - make it so
                // NOTE: The content pane flickers as it shows the cover page, then jumps to search result.
                // I tried opening the PDF at the target destination, but the same thing still happens :-(
                gEventBus.emit( "search", queryString ) ;
            } else {
                // start off showing the main ASL rulebook
                // NOTE: To avoid forcing the user to configure which document this is,
                // we assume that it's the one with the most targets.
                let targetCdocId = null ;
                for ( let cdocId in this.contentDocs ) {
                    if ( this.contentDocs[cdocId].targets == undefined )
                        continue
                    if ( targetCdocId == null || Object.keys(this.contentDocs[cdocId].targets).length > Object.keys(this.contentDocs[targetCdocId].targets).length )
                        targetCdocId = cdocId ;
                }
                if ( targetCdocId != null ) {
                    Vue.nextTick( () => {
                        gEventBus.emit( "show-page", targetCdocId, 1 ) ;
                    } ) ;
                }
            }
            // update the UI
            $( "#watermark" ).css( "opacity", 0.15 ) ;
            this.$nextTick( () => {
                $( "#query-string" ).focus() ; // nb: because autofocus on the <input> doesn't work :-/
            } ) ;
            // notify everyone that startup has completed
            this.isLoaded = true ;
            gEventBus.emit( "app-loaded" ) ;
        },

        onEscapePressed() {
            // check if there are any notification balloons open
            if ( $( ".growl" ).length > 0 ) {
                // yup - close them all
                // FUDGE! We used to trigger a click on the close button, so that the balloons would fade out,
                // but there seems to be a bug where they would just build up, hidden. Just removing them
                // from the DOM is a bit abrupt visually, but it's arguable that it's more in line with what
                // the user wants (i.e. get rid of them!)
                $( ".growl" ).each( function() {
                    $(this).remove() ;
                } ) ;
                return ;
            }
            // check if an image is currently zoomed
            if ( $(".jquery-image-zoom").length > 0 ) {
                // yup - no need to do anything here, the image will un-zoom itself
                return ;
            }
            // check if the rule info popup is open
            if ( this.$refs.navPane.closeRuleInfo() ) {
                // yup - let the Escape close it
                return ;
            }
            // if one of the non-search nav panes are open, switch to the search pane
            gEventBus.emit( "activate-tab", "nav", "search" ) ;
        },

    },

} ) ;
