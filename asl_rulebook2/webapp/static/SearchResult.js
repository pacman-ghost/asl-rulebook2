import { gMainApp } from "./MainApp.js" ;

// --------------------------------------------------------------------

export class IndexSearchResult {
    constructor( key, content ) {
        this.key = key ;
        this.srType = "index" ;
        this.content = content ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "index-sr", {

    props: [ "sr" ],

    template: `
<div class="sr index-sr" v-html=sr.content />
`,

} ) ;
