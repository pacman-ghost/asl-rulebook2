import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;
import { linkifyAutoRuleids, fixupSearchHilites, makeImagesZoomable } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "rule-info", {

    props: [ "ruleInfo" ],
    data() { return {
        closeRuleInfoImageUrl: gImagesBaseUrl + "cross.png", //eslint-disable-line no-undef
        ruleInfoTransitionName: gUrlParams.get("no-animations") ? "" : "ruleinfo-slide",
    } ; },

    // FUDGE! We want the "close" button to stay in the top-right corner of the rule info popup as the user
    // scrolls around. If we put it in together with the content itself, with an absolute position, it scrolls
    // with the content, so we place it outside the content, with an absolute position, and a larger z-index.
    // It doesn't look so good when the v-scrollbar appears, but we can live with that.
    template: `
<div>
    <img :src=closeRuleInfoImageUrl style="display:none;"
      @click="$emit('close')" ref="closeRuleInfoButton"
      title="Close the rule info" class="close-rule-info"
    />
    <transition :name=ruleInfoTransitionName @after-enter=updateCloseButton >
        <div v-show="ruleInfo.length > 0" id="rule-info" ref="ruleInfo" >
            <div class="content" ref="content">
                <div v-for="ri in ruleInfo" :key=ri >
                    <annotation v-if="ri.ri_type == 'errata'" :anno=ri />
                    <annotation v-else-if="ri.ri_type == 'user-anno'" :anno=ri />
                    <qa-entry v-else-if="ri.ri_type == 'qa'" :qaEntry=ri />
                    <div v-else> ???:{{ri.ri_type}} </div>
                </div>
            </div>
        </div>
    </transition>
</div>`,

    created() {
        // NOTE: Toggling collapsible's can cause the v-scrollbar to appear/hide.
        gEventBus.on( "collapsible-toggled", () => {
            if ( this.ruleInfo.length > 0 )
                this.updateCloseButton() ;
        } ) ;
    },

    beforeUpdate() {
        // hide the close button until the "enter" transition has completed
        let $closeButton = $( this.$refs.closeRuleInfoButton ) ;
        if ( this.ruleInfo.length == 0 )
            $closeButton.hide() ;
        else {
            if ( $closeButton.css( "display" ) == "none" )
                $closeButton.hide() ;
            else {
                // NOTE: If we're already visible, we don't get the transition, so we force
                // post-transition processing manually.
                this.$nextTick( () => {
                    this.updateCloseButton() ;
                    this.$refs.ruleInfo.scrollTop = 0 ;
                } ) ;
            }
        }
    },

    updated() {
        // make the ruleid's clickable
        linkifyAutoRuleids( $( this.$el ) ) ;
    },

    methods: {

        updateCloseButton() {
            // FUDGE! We have to wait until the rule info popup is open before we can check
            // if it has a v-scrollbar or not, and hence where we should put the close button.
            this.$nextTick( () => {
                let ruleInfo = this.$refs.ruleInfo ;
                let closeButton = this.$refs.closeRuleInfoButton ;
                if ( ruleInfo.clientHeight >= ruleInfo.scrollHeight )
                    $(closeButton).css( "right", "6px" ) ;
                else {
                    // FUDGE! The v-scrollbar is visible, so we move the "close" button left a bit.
                    // This adjustment won't update if the pane is resized, but we can live with that.
                    $(closeButton).css( "right", "18px" ) ;
                }
                $(closeButton).fadeIn( 200 ) ;
            } ) ;
        },

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "qa-entry", {

    props: [ "qaEntry" ],
    data() { return {
        questionImageUrl: gImagesBaseUrl + "question.png", //eslint-disable-line no-undef
        infoImageUrl: gImagesBaseUrl + "info.png", //eslint-disable-line no-undef
        answerImageUrl: gImagesBaseUrl + "answer.png", //eslint-disable-line no-undef
    } ; },

    template: `
<div class="qa rule-info">
    <div class="caption">
        <collapser ref="collapser" />
        <span v-html=fixupHilites(qaEntry.caption) />
    </div>
    <collapsible ref="collapsible" >
        <div v-for="content in qaEntry.content" :key=content class="content">
            <div v-if="content.question">
                <!-- this is a normal question + one or more answers -->
                <img :src=questionImageUrl class="icon" />
                <div class="question">
                    <img v-if=content.image :src=makeQAImageUrl(content.image) class="imageZoom" />
                    <div v-html=content.question />
                </div>
                <div v-for="answer in content.answers" class="answer" >
                    <img :src=answerImageUrl :title=answer[1] class="icon" />
                    <div v-html=answer[0] />
                </div>
            </div>
            <div v-else>
                <!-- this is an informational entry that contains only answers -->
                <img :src=infoImageUrl :title="content.answers.length > 0 ? content.answers[0][1] : ''" class="icon" />
                <div v-for="answer in content.answers" class="info" >
                    <div v-html=answer[0] />
                </div>
            </div>
            <div v-if=content.see_other class="see-other" >
                See other errata: <span v-html=content.see_other />
            </div>
        </div>
    </collapsible>
</div>`,

    mounted() {
        // set up the collapser
        this.$refs.collapser.initCollapser( this.$refs.collapsible, null ) ;
        // make any images that are part of the Q+A entry zoomable
        makeImagesZoomable( $(this.$el) ) ;
    },

    methods: {

        makeQAImageUrl( fname ) {
            // return the URL to an image associated with a Q+A entry
            return gGetQAImageUrl.replace( "FNAME", fname ) ; //eslint-disable-line no-undef
        },

        fixupHilites( val ) {
            // convert search term highlights returned to us by the search engine to HTML
            return fixupSearchHilites( val ) ;
        },

    },

} ) ;
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "annotation", {

    props: [ "anno" ],
    data() { return {
        annoType: this.anno.sr_type || this.anno.ri_type,
    } ; },

    template: `
<div class="anno rule-info">
    <div :class=annoType class="caption" >
        <collapser ref="collapser" />
        <span v-if=anno.ruleid :data-ruleid=anno.ruleid class="auto-ruleid"> {{anno.ruleid}} </span>
        <span v-else> (no rule ID) </span>
    </div>
    <collapsible ref="collapsible" >
        <div class="content">
            <img :src=makeIconImageUrl() :title=anno.source class="icon" />
            <div v-html=anno.content />
        </div>
    </collapsible>
</div>`,

    mounted() {
        // set up the collapser
        this.$refs.collapser.initCollapser( this.$refs.collapsible, null ) ;
    },

    methods: {
        makeIconImageUrl() {
            if ( this.annoType )
                return gImagesBaseUrl + this.annoType+".png" ; //eslint-disable-line no-undef
            else
                return null ;
        },
    },

} ) ;
