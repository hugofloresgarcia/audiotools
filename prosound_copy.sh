#!/bin/bash

# SSH and local root paths
ssh_root="hugo@malleus.cs.northwestern.edu:/media/CHONK2/prosound_core_complete/"
local_root="/media/CHONK/hugo/prosound_core_complete/"

# Define the paths to sync
paths=(
"Alan Howarth - Cinematic Dread"
"Alan Howarth - Indy Cars"
"Anns Animals"
"Avosound - City Sounds - Munich"
"Avosound - Civilisation Soundscapes 51"
"Avosound - Industrial 51 Room Tones"
"Avosound - Room Tones V01"
"Avosound - Tibetan Atmospheres"
"Avosound - Tibetan Monasteries"
"BBC Historical and 1-166 Sound Effects Library"
"BBC Nature Sound Effects Library"
"Beautiful Bugs"
"Big Room Complete"
"Big Room Update 2018"
"Biophony"
"Blastwave - Blastdrive 30"
"BTM General"
"Chicago Ambisonics"
"Chris Diebold General"
"Cinematic Winds"
"Clack"
"Detonate"
"European Capitals - Amsterdam"
"European Capitals - Berlin"
"European Capitals - London"
"European Capitals - Paris"
"European Capitals - Rome"
"European Capitals - Stockholm"
"Gators"
"Industrial Sounds with Soul"
"King Collection - Volume 1"
"London Ambisonics"
"Metalmorphosis"
"NYC Ambisonics"
"NYC Ambisonics - Volume 2"
"Paris Ambisonics"
"Print"
"Rare Animals"
"Shanghai Ambisonics"
"Sonomar Collection - Abandoned - Asylum"
"Sonomar Collection - Abandoned - Hospital"
"Sonomar Collection - Abandoned - Prison"
"Sonomar Collection - Bass Machine"
"Sonomar Collection - Crystal Sing"
"Sonomar Collection - Magnetic"
"Sonomar Collection - Pianos - Broken"
"Sonomar Collection - Pianos - Designed"
"Sonomar Collection - Pianos - Prepared"
"SoundBits - Abstract Ambiences"
"SoundBits - Buttons Switches and Levers"
"SoundBits - Cinematic Hits and Transitions"
"SoundBits - Collected Ambiences Vol 1"
"SoundBits - Collected Ambiences Vol 2"
"SoundBits - Collected Ambiences Vol 3"
"SoundBits - Collected Ambiences Vol 4"
"SoundBits - Collected Ambiences Vol 5"
"SoundBits - Collected Ambiences Vol 6"
"SoundBits - Collected Ambiences Vol 7"
"SoundBits - Collected Ambiences Vol 8"
"SoundBits - Collected Ambiences Vol 9"
"SoundBits - Computer Sound FX"
"SoundBits - Computer Sound FX 20"
"SoundBits - Crash and Smash"
"SoundBits - Crash and Smash - Designed"
"SoundBits - Dark SciFi Drones - Construction Kit"
"SoundBits - Drag and Slide"
"SoundBits - Electric Typewriters"
"SoundBits - Electro-Mechanics Toolkit"
"SoundBits - Handwriting"
"SoundBits - Just Ambiences - Construction Sites"
"SoundBits - Just Chains"
"SoundBits - Just Gore"
"SoundBits - Just Impacts"
"SoundBits - Just Impacts Extension I"
"SoundBits - Just Impacts Extension II"
"SoundBits - Just Metal"
"SoundBits - Just Stones"
"SoundBits - Just Transitions"
"SoundBits - Just Whoosh"
"SoundBits - Just Whoosh 2"
"SoundBits - Just Whoosh 3 - Whoosh Essentials"
"SoundBits - Open and Close"
"SoundBits - Open and Close 2"
"SoundBits - Pass By - FunRides"
"SoundBits - Pass By - Sports Cars"
"SoundBits - Pass By - Trains Trucks and Cars"
"SoundBits - Rummage"
"SoundBits - Screams and Shouts"
"SoundBits - Unsettling Creaks and Squeaks"
"SoundBits - Unsettling Creaks and Squeaks Extension 1"
"SoundBits - Whooshes and Impacts"
"SoundBits - Whooshes and Impacts 2"
"SoundBits - Whooshes and Impacts 2 - ELEMENTS"
"Sound Control SE Basic"
"Sound Librarian - Ambient Spaces"
"Sound Librarian - Aviation Collection"
"Sound Librarian - Firearms Foley Collection"
"Sound Librarian - The Foundation Library"
"Sound Librarian - The Telephony Collection"
"Soundmorph - Bloody Nightmare"
"Soundmorph - Cadence Weapon"
"Soundmorph - Doom Drones"
"Soundmorph - Elemental"
"Soundmorph - Energy"
"Soundmorph - Future Weapons"
"Soundmorph - Future Weapons 2"
"Soundmorph - Gore"
"Soundmorph - Intervention"
"Soundmorph - Lost Transmission"
"Soundmorph - Matter Mayhem"
"Soundmorph - Mechanism"
"Soundmorph - Modular UI - By Richard Devine"
"Soundmorph - Monster Within"
"Soundmorph - Portals"
"Soundmorph - Road Riders"
"Soundmorph - Robotic Lifeforms"
"Soundmorph - Rupture"
"Soundmorph - Sinematic"
"Soundmorph - Sinematic - Neon Expansion"
"Soundmorph - Solar Sky"
"Soundmorph - Spaces"
"Soundmorph - Steampunk Weapons"
"Soundmorph - Tension"
"Soundmorph - Transient Foundations"
"Soundmorph - Users of Tomorrow"
"Soundrangers Complete"
"Soundrangers Update 2018"
"Stallion"
"Submerged"
"test.json"
"The Odyssey Collection - Complete"
"Tokyo Ambisonics"
"train.json"
"Urban Elements"
"Useful Interface"
"val.json"
"Waves Wind Water"
"Wildlife Collection - Bengal Tiger"
"Wildlife Collection - Leopards"
)

# Function to run rsync for a single path
sync_folder() {
    local folder="$1"
    rsync -avz --progress "$ssh_root$folder/" "$local_root$folder/"
}

# Export the function and variables to be used by xargs
export -f sync_folder
export ssh_root local_root

# Run rsync in parallel for each path
printf "%s\n" "${paths[@]}" | xargs -P 8 -I {} bash -c 'sync_folder "$@"' _ {}