let vm = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        is_show_edit: false,
        form_apsa: {
            id: 0,
            onsite_type: '',
            onsite_series: '',
            facility_fin: '',
            daily_js: 0,
            temperature: 0,
            vap_max: '',
            vap_type: '',
            norminal_flow: 0,
            daily_bind: '',
            flow_meter: '',
            cooling_fixed: 0,
            comment: '',
            asset: 0,
        },
        form_site: {
            id: 0,
            uuid: '',
            cname: '',
            ename: '',
            region: '',
            engineer: 0,
            confirm: 0,
        },
        form_asset: {
            id: 0,
            name: '',
            site: 0,
            confirm: 0,
        },
        mtgroups: ['A_1', 'A_2', 'A_3', 'B_1'],
        engineer_select: {'id':1, 'name':'王文三'},
        form_engineer: {
            id: '',
            region: '',
            mtgroup: '',
            name: '',
            is_deleted: '',
        },
        form_variables: [],

        error_flag: false,
        default_address_id: '',

        //资产列表
        apsa: [],
        edit_apsa_index: '',
    },
    mounted() {
        // 获取省份数据
        this.get_apsa();
    },
    methods: {
        // 展示编辑地址弹框
        show_edit_site(index){
            this.is_show_edit = true;
            // 只获取要编辑的数据
            this.form_apsa =JSON.parse(JSON.stringify(this.apsa[index]))
            this.get_asset(this.form_apsa.asset)
            this.get_site(this.form_asset.site)
        },
        // 获取apsa数据
        get_apsa(){
            let url = '/apsa/';

            axios.get(url, {
                responseType: 'json',
                 headers: {
                        'authorization': 'JWT ' + localStorage.token
                    }
            })
                .then(response => {
                    this.apsa = response.data;
                })
                .catch(error => {
                    console.log(error.response.data)
                    if (error.response.status == 401){
                        top.location.href = '/user/login/';
                        return
                    }
                    console.log(error.response);
                    this.assets = [];
                })
        },
        get_site(pk){
            let url = '/site/' + pk + '/'
            axios.get(url, {
                responseType: 'json',
                 headers: {
                        'authorization': 'JWT ' + localStorage.token
                    }
            })
                .then(response => {
                    this.form_site = response.data;
                })
        },
        get_asset(pk){
            let url = '/asset/' + pk + '/'
            axios.get(url, {
                responseType: 'json',
                 headers: {
                        'authorization': 'JWT ' + localStorage.token
                    }
            })
                .then(response => {
                    this.form_asset = response.data;
                })
        },
        get_engineer(pk){
            let url = '/engineer/' + pk + '/'
            axios.get(url, {
                responseType: 'json',
                 headers: {
                        'authorization': 'JWT ' + localStorage.token
                    }
            })
                .then(response => {
                    this.form_engineer = response.data;
                })
        },
        // 新增地址
        save_asset(){
            if (this.error_flag) {
                alert('信息填写有误！');
            } else {
                // 注意：0 == '';返回true; 0 === '';返回false;
                if (this.editing_address_index === '') {
                    // 新增地址
                    let url = '/addresses/create/';
                    axios.post(url, this.form_address, {
                        headers: {
                            'X-CSRFToken':getCookie('csrftoken')
                        },
                        responseType: 'json'
                    })
                        .then(response => {
                            if (response.data.code == '0') {
                                // 局部刷新界面：展示所有地址信息，将新的地址添加到头部
                                this.addresses.splice(0, 0, response.data.address);
                                this.is_show_edit = false;
                            } else if (response.data.code == '4101') {
                                location.href = '/login/?next=/addresses/';
                            } else {
                                alert(response.data.errmsg);
                            }
                        })
                        .catch(error => {
                            console.log(error.response);
                        })
                } else {
                    // 修改地址
                    let url = '/addresses/' + this.addresses[this.editing_address_index].id + '/';
                    axios.put(url, this.form_address, {
                        headers: {
                            'X-CSRFToken':getCookie('csrftoken')
                        },
                        responseType: 'json'
                    })
                        .then(response => {
                            if (response.data.code == '0') {
                                this.addresses[this.editing_address_index] = response.data.address;
                                this.is_show_edit = false;
                            } else if (response.data.code == '4101') {
                                location.href = '/login/?next=/addresses/';
                            } else {
                                alert(response.data.errmsg);
                            }
                        })
                        .catch(error => {
                            alert(error.response);
                        })
                }
            }
        },
    }
});