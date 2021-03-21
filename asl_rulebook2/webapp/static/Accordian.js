import { gMainApp, gEventBus } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "accordian", {

    template: `
<div class="accordian">
    <slot />
</div>`,

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "accordian-pane", {

    props: [ "paneKey", "title", "entries", "iconUrl", "backgroundUrl" ],
    data() { return {
        isExpanded: false,
        cssBackground: this.backgroundUrl ? "url(" + this.backgroundUrl + ")": "#ccc",
    } ; },

    template: `
<div class="accordian-pane">
    <div class="title" :style="{background: cssBackground}" @click=onToggleExpand >
        <img v-if=iconUrl :src=iconUrl class="icon" />
        {{title}}
    </div>
    <ul v-show=isExpanded :class="{entries: true}" >
        <li v-for="e in entries" :key=e class="entry" :class="{disabled: !e.ruleid}" >
            <a v-if=e.ruleid @click=onClickEntry(e) > {{e.caption}} </a>
            <span v-else> {{e.caption}} </span>
        </li>
    </ul>
</div>`,

    created() {

        // handle panes being expanded
        gEventBus.on( "expand-pane", (entry) => {
            // check if we are in the same accordian as the pane being toggled
            if ( entry.$parent != this.$parent )
                return ;
            // yup - check if we are the pane being toggled
            if ( entry == this ) {
                // yup - update our state
                this.isExpanded = ! this.isExpanded ;
            } else {
                // nope - always close up (only one pane can be open at a time)
                this.isExpanded = false ;
            }
        } ) ;
    },

    methods: {
        onClickEntry( entry ) {
            // notify the parent that an entry was clicked
            this.$emit( "entry-clicked", this.paneKey, entry ) ;
        },
        onToggleExpand() {
            // notify the parent that a pane was expanded
            if ( ! this.isExpanded )
                this.$emit( "pane-expanded" ) ;
            // NOTE: Every accordian pane will receive this event, but each one
            // will figure out if it applies to them.
            gEventBus.emit( "expand-pane", this ) ;
        },
    },

} ) ;
