import { gMainApp } from "./MainApp.js" ;
import { makeImagesZoomable } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "rule-info", {

    props: [ "qaEntries" ],

    template: `
<div id="rule-info">
    <div v-for="e in qaEntries" :key=e >
        <qa-entry :qaEntry=e />
    </div>
</div>`,

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "qa-entry", {

    props: [ "qaEntry" ],
    data() { return {
        questionImageUrl: gImagesBaseUrl + "question.gif", //eslint-disable-line no-undef
        infoImageUrl: gImagesBaseUrl + "info.gif", //eslint-disable-line no-undef
        answerImageUrl: gImagesBaseUrl + "answer.gif", //eslint-disable-line no-undef
    } ; },

    template: `
<div class="qa">
    <div class="caption"> {{qaEntry.caption}} </div>
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
</div>`,

    mounted() {
        // make any images that are part of the Q+A entry zoomable
        makeImagesZoomable( $(this.$el) ) ;
    },

    methods: {
        makeQAImageUrl( fname ) {
            // return the URL to an image associated with a Q+A entry
            return gGetQAImageUrl.replace( "FNAME", fname ) ; //eslint-disable-line no-undef
        },
    },

} ) ;
