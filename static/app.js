const burger = document.querySelector(".burger");
const nav = document.querySelector("nav");

// ##############################
async function server(url, method, data_source_selector, function_after_fetch) {
    let conn = null;
    if (method.toUpperCase() == "POST") {
        const data_source = document.querySelector(data_source_selector);
        conn = await fetch(url, {
            method: method,
            body: new FormData(data_source),
        });
    }
    const data_from_server = await conn.text();
    if (!conn) {
        console.log("error connecting to the server");
    }
    window[function_after_fetch](data_from_server);
}

// ##############################
function get_search_results(
    url,
    method,
    data_source_selector,
    function_after_fetch
) {
    const txt_search_for = document.querySelector("#txt_search_for");
    if (txt_search_for.value == "") {
        console.log("empty search");
        document.querySelector("#search_results").innerHTML = "";
        document.querySelector("#search_results").classList.add("d-none");
        return false;
    }
    server(url, method, data_source_selector, function_after_fetch);
}
// ##############################
function parse_search_results(data_from_server) {
    // console.log(data_from_server)
    data_from_server = JSON.parse(data_from_server);
    let users = "";
    data_from_server.forEach((user) => {
        let user_avatar_path = user.user_avatar_path
            ? user.user_avatar_path
            : "unknown.jpg";
        let html = `
        <div class="d-flex a-items-center">
            <img src="/static/images/${user_avatar_path}" class="w-8 h-8 rounded-full" alt="Profile Picture">
            <div class="w-full ml-2">
                <p class="">
                    ${user.user_first_name} ${user.user_last_name}
                    <span class="text-c-gray:+20 text-70">@${user.user_username}</span>
                </p>                
            </div>
            <button class="px-4 py-1 text-c-white bg-c-black rounded-lg">Follow</button>
        </div>`;
        users += html;
    });
    console.log(users);
    document.querySelector("#search_results").innerHTML = users;
    document.querySelector("#search_results").classList.remove("d-none");
}

// ##############################
burger.addEventListener("click", () => {
    // toggle nav
    nav.classList.toggle("active");

    // toggle icon
    burger.classList.toggle("open");
});

//  Handle like/unlike
//  ##############################
document.addEventListener("click", async function (event) {
    const btn = event.target.closest(".like-btn");
    if (!btn) return;

    event.preventDefault();
    const postPk = btn.dataset.post;

    btn.disabled = true;

    const resp = await fetch("/toggle_like", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ post_pk: postPk }),
    });

    const data = await resp.json();

    const icon = btn.querySelector("i");
    const count = btn.querySelector(".like-count");

    count.textContent = data.like_count;

    if (data.liked) {
        icon.classList.remove("fa-regular");
        icon.classList.add("fa-solid");
    } else {
        icon.classList.remove("fa-solid");
        icon.classList.add("fa-regular");
    }

    btn.disabled = false;
});

//  ##############################
// Handles edits/deletes
document.addEventListener("click", async function (event) {
    //
    // DELETE POST
    //
    // const del = event.target.closest(".delete-btn");
    // if (del) {
    //     event.preventDefault();

    //     const postPk = del.dataset.post;

    //     // Simple confirmation popup
    //     if (!confirm("Are you sure you want to delete your post?")) return;

    //     // Send DELETE request
    //     const resp = await fetch(`/api-delete-post/${postPk}`, {
    //         method: "DELETE",
    //     });

    //     // Read the HTML (mixhtml instructions)
    //     const html = await resp.text();

    //     // Inject into DOM so mixhtml reacts to <browser> tags
    //     const temp = document.createElement("div");
    //     temp.innerHTML = html;
    //     document.body.appendChild(temp);

    //     // mixhtml processes the <browser> elements immediately
    //     temp.remove();

    //     return;
    // }

    //
    // EDIT POST
    //
    const edit = event.target.closest(".edit-btn");
    if (edit) {
        event.preventDefault();

        const postPk = edit.dataset.post;
        const textEl = document.querySelector(`#text-${postPk}`);
        const oldText = textEl.textContent.trim();

        // Ask user for updated text
        const newText = prompt("Edit your post:", oldText);
        if (newText === null) return; // User cancelled
        if (!newText.trim()) return; // Empty input not allowed

        // Send PATCH with JSON
        const resp = await fetch(`/api-edit-post/${postPk}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: newText }),
        });

        // Read the HTML mixhtml response
        const html = await resp.text();
        console.log(html);
        // Inject so mixhtml can run <browser mix-replace="#text-...">
        const temp = document.createElement("div");
        temp.innerHTML = html;
        document.body.appendChild(temp);

        temp.remove();

        return;
    }
});

// Close details when clicking
//  ##############################
document.addEventListener("click", (e) => {
    document.querySelectorAll("details.menu[open]").forEach((openMenu) => {
        if (!openMenu.contains(e.target)) {
            openMenu.removeAttribute("open");
        }
    });
});
