gMainApp.component( "main-app", {

    data() { return {
        isLoaded: false,
    } ; },

    template: `
<div> Hello, world! </div>
<div v-if="isLoaded" id="_mainapp-loaded_" />
`,

    mounted() {
        this.isLoaded = true ;
    },

} ) ;
