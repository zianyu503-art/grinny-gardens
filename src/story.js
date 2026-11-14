// All narrative text (Traditional Chinese).

export const INTRO = [
  { text: '1996 年 8 月 31 日，微笑樂園在一夜之間關閉。', dur: 4 },
  { text: '那天晚上，有二十七個孩子沒有回家。', dur: 4 },
  { text: '我曾經是這裡的維修員。我以為我再也不會回來。', dur: 4.5 },
  { text: '直到我收到那捲錄影帶。畫面裡，咪咪熊轉過頭，對著鏡頭說：', dur: 5 },
  { who: '咪咪熊', text: '「你答應過，會回來陪我們玩的。」', dur: 4 },
];

export const PA = {
  welcome: '歡迎回到微笑樂園。我們……好想你。',
  gate: '叮咚！歡迎光臨！今天也要笑著玩喔！',
  carousel: '旋轉木馬即將啟動。請小朋友坐好……不要下來。',
  funhouse: '噓……鬼屋裡，要保持安靜喔。',
  chase: '要不要……玩捉迷藏？',
  ferris: '摩天輪，是園長最喜歡的地方。',
  final: '你終於來了。',
};

export const TAPES = {
  funhouse: {
    title: '錄音帶 #1：園長',
    lines: [
      { who: '園長', text: '（沙沙）……永恆歡樂計畫，第十二次測試。' },
      { who: '園長', text: '孩子們的笑聲，可以被保存下來。保存在……柔軟的東西裡面。' },
      { who: '園長', text: '他們永遠不會長大，永遠不會難過。這難道不是最好的禮物嗎？' },
    ],
  },
  tunnel1: {
    title: '錄音帶 #2：維修日誌',
    lines: [
      { who: '我', text: '8 月 30 日。園長要我把咪咪熊的骨架加高到三公尺半。' },
      { who: '我', text: '我問為什麼。他只說：「孩子們喜歡大大的擁抱。」' },
      { who: '我', text: '今天清理牠的肚子時，我在裡面找到一隻小小的運動鞋。' },
    ],
  },
  tunnel2: {
    title: '錄音帶 #3：園長',
    lines: [
      { who: '園長', text: '測試體「咪咪熊」拒絕關機。它一直在笑……' },
      { who: '園長', text: '我們把它的嘴縫起來，它還是在笑。' },
      { who: '園長', text: '鎖上所有出口。不要讓它找到摩天輪。我在那裡。我們……都在那裡。' },
    ],
  },
};

export const ENDING = '摩天輪停了下來。所有的燈同時亮起。\n\n二十七張小小的臉貼在車廂的玻璃上，\n對著你微笑。\n\n「謝謝你回來陪我們玩。」\n「這一次，你要永遠留下來喔。」';

// ------------------------------------------------------------------ Chapter 2: the toy factory
export const INTRO2 = [
  { text: '我醒來的時候，在一台往下沉的貨梯裡。', dur: 4 },
  { text: '鐵籠外面的牆，一層一層往上滑走。', dur: 4 },
  { text: '樂園的下面，還有一座工廠。', dur: 3.5 },
  { who: '廣播', text: '「歡迎來到歡樂製造部。今天的配額……還差一點點。」', dur: 5 },
];

export const PA2 = {
  arrive: '員工請注意：笑容是我們最重要的產品。',
  sewing: '縫製部，請保持安靜。阿梅姐在工作。',
  packing: '包裝部：每一個笑聲，都要好好裝箱。',
  warehouse: '倉庫重地，閒人勿入。',
  core: '永恆歡樂機，運轉中。請勿關機。請勿關機。',
};

/** The director, holding you up to his mask before he drops you down the freight shaft. */
export const THROW = [
  { who: '園長', text: '你答應過要回來陪他們玩的。', dur: 3.4, voice: 'throw_0' },
  { who: '園長', text: '下面的孩子們……很想念你。', dur: 3.4, voice: 'throw_1' },
];

export const TAPES2 = {
  guard: {
    title: '錄音帶 #4：警衛室',
    lines: [
      { who: '警衛', text: '（沙沙）……8 月 31 日，晚上十一點。貨梯又自己下來了。' },
      { who: '警衛', text: '縫製部的燈整晚亮著。阿梅還在裡面，可是她的打卡紀錄是下午五點。' },
      { who: '警衛', text: '園長說今晚加班，不准任何人上去。……上面的小朋友呢？' },
    ],
  },
  warehouse: {
    title: '錄音帶 #5：園長',
    lines: [
      { who: '園長', text: '笑聲裝進罐子以後，就再也不會消失了。' },
      { who: '園長', text: '阿梅不懂。她想把孩子們縫回原來的樣子。所以我讓她……繼續縫。' },
      { who: '園長', text: '只要機器還在轉，他們就永遠是快樂的。永遠。' },
    ],
  },
};

export const NAME_TAG = [
  { who: '名牌', text: '「微笑樂園 · 縫製部　阿梅」', dur: 3.5 },
  { who: '我', text: '阿梅……她以前會幫我們補制服，還會偷塞糖果給迷路的小孩。', dur: 5 },
  { who: '我', text: '背面用原子筆寫著：「對不起，我縫不回去了。」', dur: 4.5 },
];

/** Mei, through the Seamstress, after the jars break (Chapter 2 ending cutscene). */
export const MEI_END = [
  { who: '阿梅', text: '孩子們……可以回家了。', dur: 3.2, voice: 'mei_end_0' },
  { who: '阿梅', text: '謝謝你。可是園長……還在摩天輪上面等你。', dur: 4.6, voice: 'mei_end_1' },
];

export const ENDING2 = '工廠安靜了下來。\n\n笑聲穿過天花板，飄向地面，\n飄向那座還亮著燈的摩天輪。\n\n你知道他在上面等你。';

/** Playback rate per speaker for the recorded tape voices: slower is deeper. */
export const VOICE_RATE = { 園長: 0.8, 我: 0.9, 警衛: 0.96 };

// ------------------------------------------------------------------ Chapter 3: lost and found
export const INTRO3 = [
  { text: '工廠的機器停了。我順著鋼索爬上去，掉進樂園地底的另一個房間。', dur: 5 },
  { text: '失物招領中心。二十七個孩子留下的東西，全都被編了號，收進鐵架裡。', dur: 5 },
  { text: '櫃檯上放著一把剪刀。是阿梅的。旁邊有一張字條。', dur: 4 },
];

export const MEI_NOTE = [
  { who: '字條', text: '「幫我把孩子們的東西找回來。影子才認得出自己。」', dur: 4.5 },
  { who: '字條', text: '「剪刀你拿去用。封條、繩子、電線，都可以剪。」', dur: 4.5 },
  { who: '字條', text: '「小心剪票的老周。沒有票的人，他一個也不會放走。」', dur: 4.5 },
];

export const PA3 = {
  hub: '失物招領中心。遺失的東西，會在這裡等你。',
  bumper: '碰碰車場，每人限乘三分鐘。請繫好安全帶。',
  tower: '維修塔，非工作人員請勿進入。',
  mirror: '鏡子迷宮。請跟著自己的影子走。',
  radio: '廣播站，現在是點播時間。有人想聽你的聲音。',
  power: '配電廠，高壓危險。請勿觸摸任何東西。',
  ticket: '驗票，請出示車票。沒有票的人，不能出去。',
};

export const TAPES3 = {
  reveal: {
    title: '錄音帶 #6：是你的聲音',
    lines: [
      { who: '我', text: '（沙沙）……8 月 31 日，凌晨一點。我在廣播室，對著麥克風說話。' },
      { who: '我', text: '園長把我叫來，說只要我照著稿子念，孩子們就能回家。' },
      { who: '我', text: '所以我念了。我鎖上了所有的出口，因為園長說，那是為了他們好，因為' },
    ],
  },
};

export const HINTS3 = {
  claw: {
    scissors: '剪刀爪：可以剪斷封條、繩子和電線。',
    magnet: '磁力爪：隔空拉動鐵門和鐵櫃，也能扯掉剪票人的鋼甲。',
    grapple: '鉤索爪：對準大鐵環發射，把自己拉過去。',
    flash: '閃光爪：照出隱藏的門，讓敵人暫時失明。',
    horn: '喇叭爪：震碎裂牆，也會用噪音把追獵者引開。',
    charge: '帶電爪：永遠帶電。可以啟動電路，電暈敵人。',
  },
  swap: '按 1–6 更換左爪，Shift + 1–6 更換右爪。',
};

export const DIRECTOR3 = [
  { who: '園長', text: '你終於把電接上了。這座樂園的燈，好久沒有這麼亮。', dur: 4.5, voice: 'dir3_0' },
  { who: '園長', text: '可是你還不明白，你為什麼會在這裡。', dur: 4, voice: 'dir3_1' },
];
export const DIRECTOR3_BROKEN = [
  { text: '人偶的頭滾到我的腳邊。裡面是空的。沒有臉，沒有人。只有一圈一圈的鋼索，一直通到更深的地方。', dur: 7 },
  { who: '園長', text: '（從很遠的地方）……你以為，我在這裡嗎？', dur: 4.5, voice: 'dir3_2' },
];

export const ENDING3 = '人偶倒在地上，不再動了。\n\n門後面是一條很深的豎井。\n鋼索從黑暗裡垂下來，一直往下，\n不知道通到哪裡。\n\n園長不在這裡。\n他從來都不在這裡。\n\n（第三章　未完）';
