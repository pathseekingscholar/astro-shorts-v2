export type AstroText = {
  content?: string;
  position?: string;
  style?: string;
};

export type AstroLayer = {
  type?: string;
  name?: string;
  position?: string;
  size?: string;
  expression?: string;
  entry_animation?: string;
  effects?: string[];
};

export type AstroScene = {
  time_start?: number;
  time_end?: number;
  layers?: AstroLayer[];
  text?: AstroText;
  screen_effects?: string[];
  dramatic_moment?: boolean;
};

export type AstroIdea = {
  title?: string;
  topic?: string;
  hook?: string;
};

export type AstroMetadata = {
  mood?: string;
  music_style?: string;
};

export type AstroScriptData = {
  idea?: AstroIdea;
  metadata?: AstroMetadata;
  timeline?: AstroScene[];
};

