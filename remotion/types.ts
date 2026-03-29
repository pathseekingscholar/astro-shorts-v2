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
  render_style?: string;
  style_hint?: string;
  style_id?: string;
  render_template?: string;
  caption_font?: string;
  background_search?: string;
  background_image_path?: string;
  music_path?: string;
  background_mode?: string;
  voice_emotion?: string;
};

export type AstroRenderPlan = {
  style_id?: string;
  selected_style_id?: string;
  render_template?: string;
  background_mode?: string;
  background_query?: string;
  background_video_path?: string;
  backgroundVideoPath?: string;
  background_image_path?: string;
  backgroundImagePath?: string;
  music_path?: string;
  musicPath?: string;
};

export type AstroScriptData = {
  idea?: AstroIdea;
  metadata?: AstroMetadata;
  timeline?: AstroScene[];
  style_id?: string;
  style_plan?: {
    style_id?: string;
    label?: string;
    render_template?: string;
  };
  renderPlan?: AstroRenderPlan;
  render_plan?: AstroRenderPlan;
  background_path?: string;
  music_path?: string;
};

export type AstroRenderProps = {
  scriptData: AstroScriptData;
  styleId?: string;
  backgroundVideoSrc?: string;
  backgroundImageSrc?: string;
  musicSrc?: string;
};
