function updateDisplay(data) {
    const container = document.getElementById('status');
    let html = '';

    data.forEach(master => {
        html += `<div class="master">
            <h2>${master.name}</h2>`;

        master.slaves.forEach(slave => {
            html += `<div class="slave">
                <h3>Slave ${slave.id}</h3>`;
//            console.log("slave:", slave)
            Object.entries(slave.data).forEach(([address, value]) => {
                address = address.substring(1, 7);
                html += `<div class="register-group">`;
                const addressStr = address.toString().padStart(6, '0');

                if (address<300000){
                    if(value){
                        html += `<div class="register">
                            <span>${addressStr}</span>
                            <input type="checkbox" checked
                                onchange="writeValue('${master.name}', ${slave.id}, ${address}, this.checked)">
                        </div>`;
                    }else{
                        html += `<div class="register">
                            <span>${addressStr}</span>
                            <input type="checkbox"
                                onchange="writeValue('${master.name}', ${slave.id}, ${address}, this.checked)">
                        </div>`;
                    }

                }else{
                    html += `<div class="register">
                        <span>${addressStr}</span>
                        <input type="number" value="${value}" step="100"
                            onchange="writeValue('${master.name}', ${slave.id}, ${address}, this.value)">
                    </div>`;
                }


                html += '</div>';
            });

            html += '</div><hr>';
        });

        html += '</div>';
    });

    container.innerHTML = html;
}

let timeoutId;

async function writeValue(master, slaveId, address, value) {
    try {
//        console.log("writeValue:", master, slaveId, address, value)
        clearTimeout(timeoutId);
        timeoutId = setTimeout(async ()=>{
            const response = await fetch('/api/write', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    master: master,
                    slave_id: slaveId,
                    address: address,
                    value: Number(value)
                })
            });

            if (!response.ok) {
                alert('Write failed!');
            }

        }, 300)

    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// 每2秒刷新数据
setInterval(() => {
    fetch('/api/status')
        .then(response => response.json())
        .then(updateDisplay)
        .catch(error => console.error('Error:', error));
}, 2000);