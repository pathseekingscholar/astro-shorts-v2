import type {AstroScriptData} from "./types";

export const sampleScriptData: AstroScriptData = {
  idea: {
    topic: "Solar Scale: Earths in the Sun",
    hook: "How many Earths can REALLY fit inside our Sun?",
    title: "1.3 Million Earths in the Sun?!"
  },
  metadata: {
    mood: "mind-blowing",
    music_style: "epic",
    render_style: "auto"
  },
  timeline: [
    {
      time_start: 0,
      time_end: 4,
      layers: [
        {type: "planet", name: "earth", position: "center", size: "medium", expression: "thinking", effects: ["idle_bounce"]}
      ],
      text: {content: "Think Earth is HUGE?", position: "top", style: "word_by_word"}
    },
    {
      time_start: 4,
      time_end: 8,
      layers: [
        {type: "planet", name: "jupiter", position: "right", size: "large", expression: "smug", effects: ["pulse"]},
        {type: "planet", name: "earth", position: "left", size: "small", expression: "looking_right", effects: ["idle_bounce"]}
      ],
      text: {content: "Jupiter alone fits 1,300 Earths!", position: "top", style: "slam_in"}
    },
    {
      time_start: 8,
      time_end: 12,
      layers: [
        {type: "planet", name: "sun", position: "center", size: "huge", expression: "happy", effects: ["pulse"]},
        {type: "planet", name: "earth", position: "bottom_left", size: "tiny", expression: "scared", effects: ["idle_bounce"]}
      ],
      text: {content: "The Sun fits... 1.3 MILLION Earths!", position: "top", style: "slam_in"},
      dramatic_moment: true
    }
  ]
};
