import datetime
import pdfkit
import requests


def pdfkit_example():
    options = {
        'page-size': 'Letter',
        # 'margin-top': None,
        # 'margin-right': None,
        # 'margin-bottom': None,
        # 'margin-left': None,
        'orientation': "Landscape",
        'encoding': "UTF-8",
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'no-outline': None
    }
    css = '/Users/alexmerryman/PycharmProjects/myco/inat-vouchers/generate_vouchers.css'
    pdfkit.from_file(input='/Users/alexmerryman/PycharmProjects/myco/inat-vouchers/generate_vouchers.html', output_path='inat_vouchers.pdf', options=options, css=css, verbose=True)


def get_inat_observations(obs_after_date: datetime.datetime.date = None, obs_after_incl_id: int = None) -> dict:
    # todo add filter_to (calendar selection when UI is built)
    base_url = "https://api.inaturalist.org/v1/observations"

    params = dict()
    taxa_include = [47170]
    params['taxon_id'] = ','.join([str(i) for i in taxa_include])
    params['user_id'] = 'alexmerryman'
    params['d1'] = ...  # Must be observed on or after this date
    params['per_page'] = 200

    if obs_after_date:
        params['d1'] = obs_after_date

    resp = requests.get(base_url, params=params)
    print(resp.url)

    all_results_page = resp.json()['results']

    if obs_after_incl_id:
        all_results_page_filtered = [r for r in all_results_page if r['id'] >= obs_after_incl_id]
    else:
        all_results_page_filtered = all_results_page

    return all_results_page_filtered


def get_obs_attributes(obs_json: dict) -> dict:

    obs_formatted = dict()
    obs_formatted['id'] = obs_json.get('id')
    obs_formatted['date_observed'] = obs_json.get('observed_on_details').get('date')

    obs_formatted['taxon_name'] = obs_json.get('taxon').get('name')
    if obs_json.get('taxon').get('rank') == 'genus':
        obs_formatted['taxon_name'] += ' sp.'

    # fill species only if rank is lower than 'family'
    if obs_json.get('taxon').get('rank') not in ['subfamily', 'supertribe', 'tribe', 'subtribe', 'genus', 'species', 'subspecies', 'variety', 'form']:
        obs_formatted['taxon_name'] = ''

    if obs_json.get('geoprivacy') == 'obscured':
        obs_formatted['location'] = ''
    else:
        obs_formatted['location'] = f"{obs_json.get('place_guess')}\n({obs_json.get('location')})"

    obs_formatted['inat_uri'] = obs_json.get('uri')

    return obs_formatted


def format_html(obs, fill_species: bool = True, fill_location: bool = True):
    if not fill_species:
        species = ''
    else:
        species = obs['taxon_name']

    if not fill_location:
        location = ''
    else:
        location = obs['location']

    voucher_box_html = f"""
    <div class="voucher-box">
        <div class="header-box">
            <p class="fungarium-logo"><img src="../static/fungarium-logo.png"></p>
            <p class="fungarium-name">The Fungarium of Alex Merryman</p>
        </div>
        <div class="body-box">
            <div class="voucher-info">
                <div style="white-space: pre-line"><b>Date</b>
                    {obs['date_observed']}
                </div>
                <div style="white-space: pre-line"><b>Fungarium ID</b>
                </div>
                <div style="white-space: pre-line"><b>Location</b>
                    {location}
                </div>
                <div style="white-space: pre-line"><b>iNaturalist ID</b>
                    {obs['id']}
                </div>
                <div style="white-space: pre-line"><b>Species</b>
                    {species}
                </div>
                <div><b>Notes</b></div>
            </div>
        </div>
    </div>"""
    return voucher_box_html


def format_html_total():
    voucher_html = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <link rel="stylesheet" href="../generate_vouchers.css">
        <link rel="stylesheet" href="https://use.typekit.net/obz8tah.css">
    </head>
    <div class="vouchers-grid">
    {OBS_HTML}
    </div>"""

    return voucher_html


def main():
    ...
    # get recent inat observation info (ID, location, datetime, etc)
    # todo add QR code to iNat uri
    # format as PDF
    # download/save to print

    # todo add print series number -- to keep track of the order the vouchers are printed in

    # pdfkit_example()

    obs = get_inat_observations(
        # obs_after_date=datetime.datetime.strptime('2024-08-20', '%Y-%m-%d')
        obs_after_incl_id=243504329
    )
    print(len(obs))

    obs_filtered = [get_obs_attributes(o) for o in obs]
    # print(obs_filtered)

    # chunk into 9s
    num_obs_per_page = 9

    obs_html_strs = [format_html(i) for i in obs_filtered]
    format_html_all = format_html_total().format(OBS_HTML='\n'.join(obs_html_strs))
    # print(format_html_all)

    out_file = f"/Users/alexmerryman/PycharmProjects/myco/inat-vouchers/generated-vouchers/vouchers_{datetime.datetime.utcnow().date()}.html"
    with open(out_file, "w") as file:
        file.write(format_html_all)


if __name__ == '__main__':
    main()
