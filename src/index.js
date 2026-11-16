
export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Bot is running!");
    }

    const update = await request.json();
    const msg = update.message;

    if (!msg || !msg.chat || msg.chat.type === "private") {
      return new Response("OK");
    }

    const chatId = String(msg.chat.id);
    const userId = String(msg.from.id);
    const key = `selected:${chatId}`;

    let selected = await env.BOT_DATA.get(key, "json") || [];

    const api = `https://api.telegram.org/bot${env.BOT_TOKEN}/`;

    async function reply(text) {
      await fetch(api + "sendMessage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: msg.chat.id,
          text,
          reply_to_message_id: msg.message_id
        })
      });
    }

    if (msg.text === "/add" && msg.reply_to_message) {
      const id = String(msg.reply_to_message.from.id);

      if (!selected.includes(id)) selected.push(id);

      await env.BOT_DATA.put(key, JSON.stringify(selected));
      await reply("فرد انتخاب شد ❤️");
      return new Response("OK");
    }

    if (msg.text === "/remove" && msg.reply_to_message) {
      const id = String(msg.reply_to_message.from.id);
      selected = selected.filter(x => x !== id);

      await env.BOT_DATA.put(key, JSON.stringify(selected));
      await reply("فرد حذف شد.");
      return new Response("OK");
    }

    if (msg.text === "/list") {
      await reply("تعداد افراد انتخاب‌شده: " + selected.length);
      return new Response("OK");
    }

    if (selected.includes(userId) && !msg.from.is_bot) {
      await fetch(api + "setMessageReaction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: msg.chat.id,
          message_id: msg.message_id,
          reaction: [{ type: "emoji", emoji: "💘" }]
        })
      });
    }

    return new Response("OK");
  }
};
