import { gMainApp, gASOPChapterIndex, gASOPSectionIndex, gEventBus } from "./MainApp.js" ;
import { getURL, getASOPChapterIdFromSectionId, linkifyAutoRuleids, wrapMatches, isChildOf } from "./utils.js" ;

let gSectionContentOverrides = {} ;

// --------------------------------------------------------------------

gMainApp.component( "asop", {

    data() { return {
        isActive: false,
        title: null,
        preamble: null,
        sections: [], isSingleSection: false,
        chapterId: null,
    } ; },

    template: `
<div v-if=isActive :data-chapterid=chapterId id="asop" class="asop" >
    <div class="title">
        <span v-html=title />
        <collapser collapserId="asop-preamble" ref="collapser" />
    </div>
    <collapsible collapsedHeight=5 ref="collapsible">
        <div v-html=preamble class="preamble" />
    </collapsible>
    <div v-if="sections.length > 0" class="sections" :class="{single: isSingleSection}" ref="sections" >
        <div v-for="s in sections" :key=s class="section" v-html=s />
    </div>
</div>
`,

    created() {

        // handle the ASOP being entered/exited
        gEventBus.on( "tab-activated", (tabbedPages, tabId) => {
            if ( ! isChildOf( tabbedPages.$el, $("#nav")[0], false ) )
                return ;
            this.isActive = (tabId == "asop") ;
        } ) ;
        gEventBus.on( "show-target", (cdocId, ruleid) => { //eslint-disable-line no-unused-vars
            this.isActive = false ;
        } ) ;

        // handle events in the nav pane
        gEventBus.on( "asop-chapter-expanded", this.showASOPChapter ) ;
        gEventBus.on( "show-asop-section", this.showASOPSection ) ;
        gEventBus.on( "show-asop-entry-sr", this.showASOPSectionSearchResult ) ;

        // remove search highlights when a new search is done
        gEventBus.on( "search", () =>  {
            gSectionContentOverrides = {} ;
        } ) ;

    },

    mounted() {
        // set up the collapser
        if ( this.$refs.collapser )
            this.$refs.collapser.initCollapser( this.$refs.collapsible, null ) ;
        // start off with the intro
        this.showIntro() ;
    },

    updated() {
        // make the ruleid's clickable
        linkifyAutoRuleids( $( this.$el ) ) ;
        // update the preamble collapser/collapsible
        if ( this.$refs.collapser )
            this.$refs.collapser.initCollapser( this.$refs.collapsible, null ) ;
        // scroll to the top of the sections each time
        if ( this.$refs.sections )
            this.$refs.sections.scrollTop = 0 ;
    },

    methods: {

        showIntro() {
            // show the ASOP intro
            this.title = "Advanced Sequence Of Play" ;
            this.preamble = null ;
            this.sections = [] ;
            this.isSingleSection = true ;
            this.chapterId = "intro" ;
            getURL( gGetASOPIntroUrl ).then( (resp) => { //eslint-disable-line no-undef
                this.sections = [ this.fixupContent( resp ) ] ;
            } ).catch( (errorMsg) => {
                // NOTE: We show the error in the content, not as a notification balloon.
                this.sections = [ "Couldn't get the ASOP intro." + " <div class='pre'>" + errorMsg + "</div>" ] ;
            } ) ;
        } ,

        showASOPChapter( chapter, isClick ) {
            if ( ! isClick )
                return ;
            // prepare to show the ASOP chapter (with all sections combined)
            this.isActive = true ;
            this.title = this.makeTitle( chapter, chapter.caption ) ;
            this.preamble = this.fixupContent( chapter.preamble ) ;
            this.sections = chapter.sections ? Array( chapter.sections.length ) : [] ;
            this.isSingleSection = false ;
            this.chapterId = chapter.chapter_id ;
            if ( this.sections.length == 0 )
                return ;
            // show each section
            let addSectionContent = (sectionNo, content) => {
                this.sections[ sectionNo ] =
                    "<div class='caption'>" + chapter.sections[sectionNo].caption + "</div>"
                    + this.fixupContent( content ) ;
            } ;
            chapter.sections.forEach( (section, sectionNo) => {
                // check if there is an override for the next section
                let sectionId = chapter.chapter_id + "-" + (1+sectionNo) ;
                let contentOverride = gSectionContentOverrides[ sectionId ] ;
                if ( contentOverride ) {
                    // yup - just use that
                    addSectionContent( sectionNo, contentOverride ) ;
                } else {
                    // nope - download the section from the backend
                    let url = gGetASOPSectionUrl.replace( "SECTION_ID", sectionId ) ; //eslint-disable-line no-undef
                    getURL( url ).then( (resp) => {
                        addSectionContent( sectionNo, resp ) ;
                    } ).catch( (errorMsg) => {
                        // NOTE: We show the error in the content, not as a notification balloon.
                        this.sections[ sectionNo ] =
                            "Couldn't get ASOP section <tt>" + sectionId + "</tt>."
                            + " <div class='pre'>" + errorMsg + "</div>" ;
                    } ) ;
                }
            } ) ;
        },

        showASOPSection( chapter, section ) {
            this.doShowASOPSection( chapter, section, "" ) ;
            // show the specified ASOP section
            let sectionId = section.section_id ;
            let url = gGetASOPSectionUrl.replace( "SECTION_ID", sectionId ) ; //eslint-disable-line no-undef
            getURL( url ).then( (resp) => {
                this.doShowASOPSection( chapter, section, resp ) ;
            } ).catch( (errorMsg) => {
                // NOTE: We show the error in the content, not as a notification balloon.
                this.sections = [
                    "Couldn't get ASOP section <tt>"+sectionId+"</tt>." + " <div class='pre'>" + errorMsg + "</div>"
                ] ;
            } ) ;
        },

        showASOPSectionSearchResult( sectionId, content ) {
            // show the specified ASOP section
            let chapterId = getASOPChapterIdFromSectionId( sectionId ) ;
            let chapter = gASOPChapterIndex[ chapterId ] ;
            if ( ! chapter ) {
                console.log( "INTERNAL ERROR: Can't find parent chapter for section ID: " + sectionId ) ;
                return ;
            }
            let section = gASOPSectionIndex[ sectionId ] ;
            if ( ! section ) {
                console.log( "INTERNAL ERROR: Can't find section ID: " + sectionId ) ;
                return ;
            }
            gSectionContentOverrides[ sectionId ] = content ;
            this.doShowASOPSection( chapter, section, content ) ;
        },

        doShowASOPSection( chapter, section, content ) {
            // show the specified ASOP section
            this.isActive = true ;
            this.title = this.makeTitle( chapter, section.caption ) ;
            this.preamble = this.fixupContent( chapter.preamble ) ;
            let contentOverride = gSectionContentOverrides[ section.section_id ] ;
            this.sections = [ this.fixupContent( contentOverride || content ) ] ;
            this.isSingleSection = true ;
            this.chapterId = chapter.chapter_id ;
        },

        makeTitle( chapter, caption ) {
            // generate a chapter title
            if ( chapter.sniper_phase )
                caption += "<sup><span title='Sniper Attacks/Checks are possible during this phase.'>&dagger;</span></sup>" ;
            return caption ;
        },

        fixupContent( content ) {
            return wrapMatches(
                content,
                new RegExp( /\[EXC: .*?\]/g ),
                "<span class='exc'>", "</span>"
            ) ;
        },

    },

} ) ;
