import { gMainApp, gUrlParams } from "./MainApp.js" ;
import { linkifyAutoRuleids, fixupSearchHilites, makeImagesZoomable, makeImageUrl } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "rule-info", {

    props: [ "ruleInfo" ],
    data() { return {
        closeRuleInfoImageUrl: makeImageUrl( "close-popup.png" ),
        ruleInfoTransitionName: gUrlParams.get("no-animations") ? "" : "ruleinfo-slide",
    } ; },

    // NOTE: We have 3 separate transitions to try get the animation timing to look right :-/
    template: `
<div>
    <transition :name=ruleInfoTransitionName >
        <div v-show=showPopup() id="rule-info-overlay" />
    </transition>
    <transition :name=ruleInfoTransitionName >
        <div v-show=showPopup() id="rule-info" ref="ruleInfo" >
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
    <transition :name=ruleInfoTransitionName >
        <img v-if=showPopup() :src=closeRuleInfoImageUrl
          @click="$emit('close')" ref="closeRuleInfoButton"
          class="close-rule-info"
        />
    </transition>
</div>`,

    beforeUpdate() {
        this.$nextTick( () => {
            this.$refs.ruleInfo.scrollTop = 0 ;
        } ) ;
    },

    updated() {
        // make the ruleid's clickable
        linkifyAutoRuleids( $( this.$el ) ) ;
    },

    methods: {

        showPopup() {
            // figure out if the popup should be shown
            return this.ruleInfo.length > 0 ;
        },

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "qa-entry", {

    props: [ "qaEntry" ],
    data() { return {
        questionImageUrl: makeImageUrl( "question.png" ),
        infoImageUrl: makeImageUrl( "info.png" ),
        answerImageUrl: makeImageUrl( "answer.png" ),
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
                return makeImageUrl( this.annoType + ".png" ) ;
            else
                return null ;
        },
    },

} ) ;
